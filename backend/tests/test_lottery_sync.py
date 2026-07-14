from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.plugins.lottery.application import services
from app.plugins.lottery.application.services import LotteryService
from app.plugins.lottery.domain.constants import DLT_GAME_CODE
from app.plugins.lottery.domain.sync import DrawRecord, DrawSourcePage, DrawSyncCommand
from app.plugins.lottery.infrastructure.persistence.repositories import LotteryRepository
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


class FakeSportteryDrawSource:
    source = "sporttery"
    base_url = "https://example.test/dlt"

    def __init__(self, timeout_seconds: int = 30) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch_page(self, page: int, page_size: int) -> DrawSourcePage:
        return DrawSourcePage(
            source=self.source,
            source_url=self.base_url,
            records=[
                DrawRecord(
                    game_code=DLT_GAME_CODE,
                    issue_no="25082",
                    draw_date=date(2026, 7, 14),
                    front_numbers=[1, 2, 3, 4, 5],
                    back_numbers=[6, 7],
                    sales_amount=Decimal("123456.78"),
                    pool_amount=Decimal("987654.32"),
                    source_url=self.base_url,
                    raw_data={"issue": "25082"},
                )
            ],
            raw_metadata={"fixture": True},
        )


class FailingSportteryDrawSource:
    source = "sporttery"
    base_url = "https://example.test/dlt"

    def __init__(self, timeout_seconds: int = 30) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch_page(self, page: int, page_size: int) -> DrawSourcePage:
        raise AppError(
            code=ErrorCode.lottery_sync_source_unavailable,
            message="source unavailable",
            status_code=502,
        )


def test_sync_draws_inserts_and_skips_existing_data(
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(services, "SportteryDrawSource", FakeSportteryDrawSource)
    LotteryRepository(db_session).ensure_dlt_seed_data()
    service = LotteryService(db_session)

    first = service.sync_draws(DrawSyncCommand(page=1, page_size=100))
    second = service.sync_draws(DrawSyncCommand(page=1, page_size=100))

    assert first["status"] == "success"
    assert first["inserted_count"] == 1
    assert first["latest_issue_no"] == "25082"
    assert second["status"] == "success"
    assert second["skipped_count"] == 1
    assert service.get_latest_draw()["issue_no"] == "25082"


def test_sync_draws_returns_failed_run_when_source_is_unavailable(
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(services, "SportteryDrawSource", FailingSportteryDrawSource)
    LotteryRepository(db_session).ensure_dlt_seed_data()
    service = LotteryService(db_session)

    result = service.sync_draws(DrawSyncCommand(page=1, page_size=100))

    assert result["status"] == "failed"
    assert result["failed_count"] == 1
    assert result["error_code"] == "LOTTERY_SYNC_SOURCE_UNAVAILABLE"


def test_latest_sync_run_without_data_returns_domain_error(client: TestClient) -> None:
    response = client.get("/api/v1/lottery/dlt/sync/latest")

    assert response.status_code == 404
    assert response.json()["code"] == "LOTTERY_SYNC_RUN_NOT_FOUND"
