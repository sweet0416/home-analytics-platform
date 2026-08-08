from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config.settings import get_settings
from app.plugins.fund.infrastructure.persistence.repositories import FundRepository
from app.plugins.fund.infrastructure.sources.ttskill import (
    TtSkillAccountHoldingSource,
    TtSkillBaseInfoSource,
)
from app.plugins.fund.infrastructure.sources.ttskill_nav import TtSkillNavInfoSource
from app.shared.exceptions.base import AppError


def _base_infos_payload() -> dict[str, object]:
    return {
        "code": 0,
        "message": "success",
        "data": {
            "skill_id": "TTFUND_BASE_INFOS",
            "raw_result": {
                "status_code": 200,
                "body": {
                    "success": True,
                    "data": [
                        {
                            "FCODE": "009777",
                            "SHORTNAME": "中欧阿尔法混合C",
                            "FTYPE": "混合型-偏股",
                            "FSRQ": "2026-08-07",
                            "DWJZ": 0.7748,
                            "LJJZ": 0.7748,
                        }
                    ],
                },
            },
        },
    }


def _account_holdings_payload(asset_value: str = "8000.00") -> dict[str, object]:
    return {
        "code": 0,
        "message": "success",
        "data": {
            "skill_id": "ACCOUNT_HOLDING",
            "raw_result": {
                "status_code": 200,
                "body": {
                    "success": True,
                    "action": "holding_list",
                    "firstError": None,
                    "holding_list_result": [
                        {
                            "fundName": "中欧阿尔法混合C",
                            "fundCode": "009777",
                            "assetValue": asset_value,
                            "dailyProfit": "12.50",
                            "holdProfit": "250.00",
                            "holdProfitRate": "3.23%",
                            "constantProfit": "300.00",
                            "constantProfitRate": "3.90%",
                            "pType": "fund",
                        }
                    ],
                },
            },
        },
    }


def test_ttskill_source_parses_base_infos() -> None:
    latest = TtSkillBaseInfoSource().parse(_base_infos_payload())

    assert latest.fund_code == "009777"
    assert latest.fund_name == "中欧阿尔法混合C"
    assert latest.unit_nav == Decimal("0.7748")
    assert latest.source == "ttfund_skills"


def test_ttskill_nav_info_source_parses_latest_history_item() -> None:
    payload = {
        "code": 0,
        "data": {
            "skill_id": "TTFUND_NAV_INFO",
            "raw_result": {
                "status_code": 200,
                "body": {
                    "success": True,
                    # TTFUND_NAV_INFO 1.1.1 may return this alias while the
                    # payload contract remains unchanged.
                    "action": "query_by_code",
                    "data": {
                        "fund_profile": {
                            "fund_code": "009777",
                            "fund_name": "中欧阿尔法混合C",
                            "fund_type": "混合型-偏股",
                        },
                        "nav_history": {
                            "items": {
                                "FSRQ": ["2026-08-06", "2026-08-07"],
                                "DWJZ": ["0.7700", "0.7748"],
                                "LJJZ": ["0.7700", "0.7748"],
                            }
                        },
                    },
                },
            },
        },
    }
    latest = TtSkillNavInfoSource().parse(payload)
    assert latest.fund_code == "009777"
    assert latest.nav_date == date(2026, 8, 7)
    assert latest.unit_nav == Decimal("0.7748")


def test_ttskill_source_rejects_ambiguous_response() -> None:
    payload = _base_infos_payload()
    body = payload["data"]["raw_result"]["body"]  # type: ignore[index]
    body["data"] = []  # type: ignore[index]

    try:
        TtSkillBaseInfoSource().parse(payload)
    except AppError as exc:
        assert exc.code == "FUND_TTSKILL_PARSE_FAILED"
    else:
        raise AssertionError("Expected an AppError for an empty response.")


def test_ttskill_source_parses_account_holdings() -> None:
    holdings = TtSkillAccountHoldingSource().parse(_account_holdings_payload())

    assert len(holdings) == 1
    assert holdings[0].asset_code == "009777"
    assert holdings[0].asset_value == Decimal("8000.00")
    assert holdings[0].hold_profit_rate == Decimal("0.0323")


def test_ttskill_source_rejects_summary_response() -> None:
    payload = {
        "code": 0,
        "data": {
            "skill_id": "ACCOUNT_HOLDING",
            "raw_result": {"status_code": 200, "body": {"success": True}},
        },
    }

    try:
        TtSkillAccountHoldingSource().parse(payload)
    except AppError as exc:
        assert exc.code == "FUND_TTSKILL_PARSE_FAILED"
    else:
        raise AssertionError("Expected an AppError for a summary response.")


def test_ttskill_import_requires_token(client: TestClient) -> None:
    settings = get_settings().model_copy(
        update={
            "fund_ttskill_sync_enabled": True,
            "fund_ttskill_sync_token": "test-sync-token",
        }
    )
    client.app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = client.post(
            "/api/v1/fund/integrations/ttskill/base-infos",
            json=_base_infos_payload(),
        )
    finally:
        client.app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 401
    assert response.json()["code"] == "FUND_TTSKILL_UNAUTHORIZED"


def test_ttskill_import_persists_fund_and_nav(
    client: TestClient,
    db_session: Session,
) -> None:
    settings = get_settings().model_copy(
        update={
            "fund_ttskill_sync_enabled": True,
            "fund_ttskill_sync_token": "test-sync-token",
        }
    )
    client.app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = client.post(
            "/api/v1/fund/integrations/ttskill/base-infos",
            headers={"X-HAP-Sync-Token": "test-sync-token"},
            json=_base_infos_payload(),
        )
    finally:
        client.app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 200
    result = response.json()["data"]
    assert result["fund_code"] == "009777"
    assert result["fund_name"] == "中欧阿尔法混合C"
    assert result["source"] == "ttfund_skills"

    repository = FundRepository(db_session)
    fund = repository.get_fund_by_code("009777")
    assert fund is not None
    assert fund.source == "ttfund_skills"
    records = repository.list_nav_history(fund_code="009777", limit=1)
    assert records[0].unit_nav == Decimal("0.7748")


def test_ttskill_account_import_requires_token(client: TestClient) -> None:
    settings = get_settings().model_copy(
        update={
            "fund_ttskill_sync_enabled": True,
            "fund_ttskill_sync_token": "test-sync-token",
        }
    )
    client.app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = client.post(
            "/api/v1/fund/integrations/ttskill/holdings",
            json=_account_holdings_payload(),
        )
    finally:
        client.app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 401
    assert response.json()["code"] == "FUND_TTSKILL_UNAUTHORIZED"


def test_ttskill_account_snapshot_compares_manual_positions(
    client: TestClient,
) -> None:
    position_response = client.post(
        "/api/v1/fund/positions",
        json={
            "fund_code": "009777",
            "fund_name": "中欧阿尔法混合C",
            "fund_type": "混合型-偏股",
            "account_name": "默认账户",
            "shares": 10000,
            "cost_price": 0.75,
            "current_nav": 0.7748,
            "tags": "",
            "note": "",
        },
    )
    assert position_response.status_code == 200

    settings = get_settings().model_copy(
        update={
            "fund_ttskill_sync_enabled": True,
            "fund_ttskill_sync_token": "test-sync-token",
        }
    )
    client.app.dependency_overrides[get_settings] = lambda: settings
    try:
        first_response = client.post(
            "/api/v1/fund/integrations/ttskill/holdings",
            headers={"X-HAP-Sync-Token": "test-sync-token"},
            json=_account_holdings_payload("8000.00"),
        )
        second_response = client.post(
            "/api/v1/fund/integrations/ttskill/holdings",
            headers={"X-HAP-Sync-Token": "test-sync-token"},
            json=_account_holdings_payload("8100.00"),
        )
    finally:
        client.app.dependency_overrides.pop(get_settings, None)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    latest_response = client.get(
        "/api/v1/fund/integrations/ttskill/holdings/latest"
    )
    assert latest_response.status_code == 200
    snapshot = latest_response.json()["data"]
    assert snapshot["id"] == second_response.json()["data"]["id"]
    assert snapshot["holding_count"] == 1
    assert snapshot["total_asset_value"] == "8100.00"
    assert snapshot["matched_count"] == 1
    assert snapshot["items"][0]["manual_current_value"] == "7748.00000000"
    assert snapshot["items"][0]["value_difference"] == "352.00000000"
    assert snapshot["items"][0]["comparison_status"] == "matched"


def test_ttskill_account_latest_returns_none_without_snapshot(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/fund/integrations/ttskill/holdings/latest")

    assert response.status_code == 200
    assert response.json()["data"] is None
