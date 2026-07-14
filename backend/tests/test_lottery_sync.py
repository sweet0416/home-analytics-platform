from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.plugins.lottery.application import services
from app.plugins.lottery.application.services import LotteryService
from app.plugins.lottery.domain.constants import DLT_GAME_CODE
from app.plugins.lottery.domain.sync import DrawRecord, DrawSourcePage, DrawSyncCommand
from app.plugins.lottery.infrastructure.persistence.repositories import LotteryRepository
from app.plugins.lottery.infrastructure.sources.five_hundred import FiveHundredDrawSource
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


class FakeSportteryDrawSource:
    source = "sporttery"
    base_url = "https://example.test/dlt"

    def __init__(self, timeout_seconds: int = 30, base_url: str | None = None) -> None:
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url or type(self).base_url

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

    def __init__(self, timeout_seconds: int = 30, base_url: str | None = None) -> None:
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url or type(self).base_url

    def fetch_page(self, page: int, page_size: int) -> DrawSourcePage:
        raise AppError(
            code=ErrorCode.lottery_sync_source_unavailable,
            message="source unavailable",
            status_code=502,
        )


class FakeFiveHundredDrawSource(FakeSportteryDrawSource):
    source = "500_lottery"
    base_url = "https://example.test/500-dlt"


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
    monkeypatch.setattr(services, "FiveHundredDrawSource", FailingSportteryDrawSource)
    LotteryRepository(db_session).ensure_dlt_seed_data()
    service = LotteryService(db_session)

    result = service.sync_draws(DrawSyncCommand(page=1, page_size=100))

    assert result["status"] == "failed"
    assert result["failed_count"] == 1
    assert result["error_code"] == "LOTTERY_SYNC_SOURCE_UNAVAILABLE"


def test_sync_draws_uses_fallback_source_when_official_source_fails(
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(services, "SportteryDrawSource", FailingSportteryDrawSource)
    monkeypatch.setattr(services, "FiveHundredDrawSource", FakeFiveHundredDrawSource)
    LotteryRepository(db_session).ensure_dlt_seed_data()

    result = LotteryService(db_session).sync_draws(DrawSyncCommand(page=1, page_size=100))

    assert result["status"] == "success"
    assert result["source"] == "500_lottery"
    assert result["inserted_count"] == 1
    assert result["error_code"] is None


def test_five_hundred_source_parses_history_table() -> None:
    html = """
    <table id="tablelist">
      <tr><td>期号</td></tr>
      <tr>
        <td>26078</td>
        <td class="cfont2">02</td><td class="cfont2">13</td>
        <td class="cfont2">20</td><td class="cfont2">25</td>
        <td class="cfont2">32</td><td class="cfont4">08</td>
        <td class="cfont4">11</td><td>818,797,138</td>
        <td>5</td><td>8,216,073</td><td>181</td><td>70,136</td>
        <td>302,935,941</td><td>2026-07-13</td>
      </tr>
    </table>
    """

    records = FiveHundredDrawSource().parse_html(
        html,
        "https://datachart.500.com/dlt/history/newinc/history.php?limit=30&sort=0",
    )

    assert len(records) == 1
    assert records[0].issue_no == "26078"
    assert records[0].front_numbers == [2, 13, 20, 25, 32]
    assert records[0].back_numbers == [8, 11]
    assert records[0].pool_amount == Decimal("818797138")
    assert records[0].sales_amount == Decimal("302935941")
    assert records[0].draw_date == date(2026, 7, 13)


def test_latest_sync_run_without_data_returns_domain_error(client: TestClient) -> None:
    response = client.get("/api/v1/lottery/dlt/sync/latest")

    assert response.status_code == 404
    assert response.json()["code"] == "LOTTERY_SYNC_RUN_NOT_FOUND"
