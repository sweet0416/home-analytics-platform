from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.plugins.fund.infrastructure.persistence.repositories import (
    FundRepository,
)


def test_lookthrough_api_returns_persisted_current_snapshot(
    client: TestClient,
    db_session: Session,
) -> None:
    response = client.post(
        "/api/v1/fund/positions",
        json={
            "fund_code": "009777",
            "fund_name": "Sample Fund",
            "fund_type": "mixed",
            "account_name": "Default",
            "shares": "100",
            "cost_price": "1.0000",
            "current_nav": "1.0000",
            "tags": "",
            "note": "",
        },
    )
    assert response.status_code == 200

    repository = FundRepository(db_session)
    fund = repository.get_fund_by_code("009777")
    assert fund is not None
    repository.upsert_disclosure(
        fund=fund,
        report_date=datetime.now(ZoneInfo("Asia/Shanghai")).date(),
        report_period="2026Q2",
        asset_type="stock",
        source="test",
        source_url="https://example.test",
        holdings=[
            (
                1,
                "stock",
                "300308",
                "中际旭创",
                Decimal("0.10"),
                None,
                None,
            )
        ],
    )
    repository.commit()

    response = client.get("/api/v1/fund/holdings/lookthrough")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["fund_count"] == 1
    assert body["current_disclosure_count"] == 1
    assert body["coverage_weight"] == "1.00000000"
    assert body["assets"][0]["asset_code"] == "300308"


def test_target_link_api_creates_updates_and_deletes(
    client: TestClient,
) -> None:
    payload = {
        "parent_fund_code": "050025",
        "target_fund_code": "513500",
        "target_fund_name": "博时标普500ETF",
        "target_allocation_ratio": "0.9402",
        "report_date": "2026-03-31",
        "source_url": "https://example.test/report.pdf",
    }
    response = client.post(
        "/api/v1/fund/holdings/lookthrough/target-links",
        json=payload,
    )
    assert response.status_code == 200
    assert response.json()["data"]["origin"] == "database"

    response = client.get("/api/v1/fund/holdings/lookthrough/target-links")
    assert response.status_code == 200
    assert response.json()["data"][0]["target_fund_code"] == "513500"

    payload["target_allocation_ratio"] = "0.9100"
    response = client.post(
        "/api/v1/fund/holdings/lookthrough/target-links",
        json=payload,
    )
    assert response.status_code == 200
    assert response.json()["data"]["target_allocation_ratio"] == "0.91000000"

    response = client.delete(
        "/api/v1/fund/holdings/lookthrough/target-links/050025"
    )
    assert response.status_code == 200
    assert response.json()["data"]["deleted"] is True

    response = client.get("/api/v1/fund/holdings/lookthrough/target-links")
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_target_link_api_rejects_invalid_relationship(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/fund/holdings/lookthrough/target-links",
        json={
            "parent_fund_code": "050025",
            "target_fund_code": "050025",
            "target_fund_name": "Invalid",
            "target_allocation_ratio": "1.2",
            "report_date": "2026-03-31",
            "source_url": "not-a-url",
        },
    )

    assert response.status_code == 422
