from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.config.settings import get_settings
from app.plugins.fund.infrastructure.sources.ttskill_trades import (
    TtSkillTradeQuerySource,
)


def _envelope(action: str, result_key: str, result: dict) -> dict:
    return {
        "code": 0,
        "data": {
            "skill_id": "TRADE_QUERY",
            "raw_result": {
                "status_code": 200,
                "body": {"success": True, "action": action, result_key: result},
            },
        },
    }


def test_trade_bundle_parses_confirmed_buy() -> None:
    trade_id = "trade-1"
    list_payload = _envelope(
        "trade_list",
        "trade_list_result",
        {"totalCount": 1, "trades": [{"tradeId": trade_id}]},
    )
    detail_payload = _envelope(
        "trade_detail",
        "trade_detail_result",
        {
            "tradeId": trade_id,
            "tradeType": "fund",
            "fundCode": "009777",
            "fundName": "中欧阿尔法混合C",
            "businessCode": "22",
            "businessType": "买入",
            "tradeTime": "2026-07-16 14:48:08",
            "statusText": "查看盈亏",
            "confirmed": True,
            "confirmStatus": "confirmed",
            "applyAmount": "100.00元",
            "confirmAmount": "100.00",
            "confirmVol": "119.43",
            "nav": "0.8373",
            "confirmDate": "2026-07-17",
            "charge": "0.00",
        },
    )

    trade = TtSkillTradeQuerySource().parse_bundle(
        list_payload, [detail_payload]
    ).trades[0]

    assert trade.transaction_type == "buy"
    assert trade.effective_amount == Decimal("100.00")
    assert trade.confirm_date == date(2026, 7, 17)
    assert trade.confirm_vol == Decimal("119.43")


def test_cancelled_trade_is_not_a_cash_flow_transaction() -> None:
    trade_id = "trade-cancelled"
    list_payload = _envelope(
        "trade_list",
        "trade_list_result",
        {"totalCount": 1, "trades": [{"tradeId": trade_id}]},
    )
    detail_payload = _envelope(
        "trade_detail",
        "trade_detail_result",
        {
            "tradeId": trade_id,
            "tradeType": "fund",
            "fundCode": "009776",
            "fundName": "中欧阿尔法混合A",
            "businessCode": "22",
            "businessType": "买入",
            "tradeTime": "2026-07-13 15:12:22",
            "statusText": "已撤单",
            "confirmed": False,
            "confirmStatus": "cancelled",
            "applyAmount": "300.00元",
            "confirmAmount": "--",
            "confirmVol": "--",
            "nav": "--",
            "confirmDate": None,
            "charge": "0.00",
        },
    )

    trade = TtSkillTradeQuerySource().parse_bundle(
        list_payload, [detail_payload]
    ).trades[0]

    assert trade.transaction_type is None


def test_trade_list_accepts_empty_success_without_result_container() -> None:
    payload = _envelope("trade_list", "message", "no trades")
    assert TtSkillTradeQuerySource().parse_bundle(payload, []).trades == ()


def test_trade_list_accepts_trade_list_alias() -> None:
    trade_id = "trade-alias"
    payload = _envelope(
        "trade_list",
        "tradeListResult",
        {"items": [{"trade_id": trade_id}]},
    )
    assert TtSkillTradeQuerySource()._list_rows(payload)[0]["trade_id"] == trade_id


def test_trade_import_preview_then_apply_is_idempotent(client: TestClient) -> None:
    trade_id = "trade-import-1"
    payload = {
        "list_payload": _envelope(
            "trade_list",
            "trade_list_result",
            {"totalCount": 1, "trades": [{"tradeId": trade_id}]},
        ),
        "detail_payloads": [
            _envelope(
                "trade_detail",
                "trade_detail_result",
                {
                    "tradeId": trade_id,
                    "tradeType": "fund",
                    "fundCode": "009777",
                    "fundName": "中欧阿尔法混合C",
                    "businessCode": "22",
                    "businessType": "买入",
                    "tradeTime": "2026-07-16 14:48:08",
                    "statusText": "查看盈亏",
                    "confirmed": True,
                    "confirmStatus": "confirmed",
                    "applyAmount": "100.00元",
                    "confirmAmount": "100.00",
                    "confirmVol": "119.43",
                    "nav": "0.8373",
                    "confirmDate": "2026-07-17",
                    "charge": "0.00",
                },
            )
        ],
        "account_name": "天天基金",
    }
    settings = get_settings().model_copy(
        update={"fund_ttskill_sync_enabled": True, "fund_ttskill_sync_token": "test-token"}
    )
    client.app.dependency_overrides[get_settings] = lambda: settings
    try:
        preview = client.post(
            "/api/v1/fund/integrations/ttskill/trades/preview",
            headers={"X-HAP-Sync-Token": "test-token"},
            json=payload,
        )
        applied = client.post(
            "/api/v1/fund/integrations/ttskill/trades/import",
            headers={"X-HAP-Sync-Token": "test-token"},
            json=payload,
        )
        repeated = client.post(
            "/api/v1/fund/integrations/ttskill/trades/import",
            headers={"X-HAP-Sync-Token": "test-token"},
            json=payload,
        )
    finally:
        client.app.dependency_overrides.pop(get_settings, None)

    assert preview.status_code == 200
    assert preview.json()["data"]["create_count"] == 1
    assert applied.status_code == 200
    assert applied.json()["data"]["create_count"] == 1
    assert repeated.status_code == 200
    assert repeated.json()["data"]["update_count"] == 1
