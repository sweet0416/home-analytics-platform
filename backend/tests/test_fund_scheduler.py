from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.plugins.fund.jobs import scheduler


def test_scheduled_sync_marks_day_complete_after_new_nav(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeDb:
        closed = False

        def close(self) -> None:
            self.closed = True

    class FakeService:
        def __init__(self, repository: object, settings: object) -> None:
            self.repository = repository
            self.settings = settings

        def sync_tracked_navs(self) -> SimpleNamespace:
            return SimpleNamespace(total=4, succeeded=4, failed=0, updated=2)

    fake_db = FakeDb()
    monkeypatch.setattr(scheduler, "_completed_date", None)
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(scheduler, "FundRepository", lambda db: object())
    monkeypatch.setattr(scheduler, "FundService", FakeService)
    monkeypatch.setattr(scheduler, "get_settings", lambda: SimpleNamespace())

    scheduler._run_scheduled_fund_nav_sync()

    today = datetime.now(ZoneInfo(scheduler.TIMEZONE)).date()
    assert scheduler._completed_date == today
    assert scheduler._last_run is not None
    assert scheduler._last_run["status"] == "succeeded"
    assert scheduler._last_run["updated"] == 2
    assert scheduler._last_run["skipped"] is False
    assert fake_db.closed is True


def test_scheduled_sync_skips_after_data_updated_today(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_session() -> None:
        raise AssertionError("database should not open")

    today = datetime.now(ZoneInfo(scheduler.TIMEZONE)).date()
    monkeypatch.setattr(scheduler, "_completed_date", today)
    monkeypatch.setattr(scheduler, "SessionLocal", fail_session)

    scheduler._run_scheduled_fund_nav_sync()

    assert scheduler._last_run is not None
    assert scheduler._last_run["status"] == "succeeded"
    assert scheduler._last_run["skipped"] is True
    assert scheduler._last_run["updated"] == 0
