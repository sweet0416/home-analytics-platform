from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config.settings import get_settings
from app.plugins.fund.infrastructure.persistence.repositories import FundRepository
from app.plugins.fund.infrastructure.sources.ttskill import TtSkillBaseInfoSource
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


def test_ttskill_source_parses_base_infos() -> None:
    latest = TtSkillBaseInfoSource().parse(_base_infos_payload())

    assert latest.fund_code == "009777"
    assert latest.fund_name == "中欧阿尔法混合C"
    assert latest.unit_nav == Decimal("0.7748")
    assert latest.source == "ttfund_skills"


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
