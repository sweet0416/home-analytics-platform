from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import Session

from app.plugins.fund.infrastructure.persistence.repositories import FundRepository
from app.plugins.fund.jobs import scheduler


class FakeRepository:
    def __init__(self, db: object) -> None:
        self.db = db
        self.committed = False

    def create_nav_sync_run(self, **values: object) -> SimpleNamespace:
        return SimpleNamespace(id=1, **values)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


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
    monkeypatch.setattr(scheduler, "FundRepository", FakeRepository)
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
    class FakeDb:
        def close(self) -> None:
            pass

    today = datetime.now(ZoneInfo(scheduler.TIMEZONE)).date()
    monkeypatch.setattr(scheduler, "_completed_date", today)
    monkeypatch.setattr(scheduler, "SessionLocal", FakeDb)
    monkeypatch.setattr(scheduler, "FundRepository", FakeRepository)

    scheduler._run_scheduled_fund_nav_sync()

    assert scheduler._last_run is not None
    assert scheduler._last_run["status"] == "succeeded"
    assert scheduler._last_run["skipped"] is True
    assert scheduler._last_run["updated"] == 0


def test_nav_sync_run_is_persisted(db_session: Session) -> None:
    repository = FundRepository(db_session)
    now = datetime.now(ZoneInfo(scheduler.TIMEZONE))

    created = repository.create_nav_sync_run(
        trigger_type="scheduled",
        status="succeeded",
        started_at=now,
        finished_at=now,
        total=4,
        succeeded=4,
        failed=0,
        updated=3,
        skipped=False,
        message="saved",
    )
    repository.commit()

    latest = repository.get_latest_nav_sync_run()
    latest_updated = repository.get_latest_updated_nav_sync_run()
    assert latest is not None
    assert latest.id == created.id
    assert latest.updated == 3
    assert latest_updated is not None
    assert latest_updated.id == created.id
