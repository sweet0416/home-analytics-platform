from datetime import date, datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.core.config.settings import get_settings
from app.core.database.session import SessionLocal
from app.plugins.fund.application.services import FundService
from app.plugins.fund.infrastructure.persistence.models import FundNavSyncRunModel
from app.plugins.fund.infrastructure.persistence.repositories import FundRepository

TIMEZONE = "Asia/Shanghai"
JOB_ID = "fund_nav_auto_sync"

_scheduler: BackgroundScheduler | None = None
_last_run: dict[str, object] | None = None
_completed_date: date | None = None


def start_fund_scheduler() -> None:
    settings = get_settings()
    if not settings.fund_nav_auto_sync_enabled:
        logger.info("Fund NAV auto sync is disabled.")
        return

    global _completed_date, _last_run, _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.info("Fund NAV auto sync scheduler is already running.")
        return

    db = SessionLocal()
    try:
        repository = FundRepository(db)
        latest_run = repository.get_latest_nav_sync_run()
        if latest_run is not None:
            _last_run = _run_to_dict(latest_run)
        latest_updated_run = repository.get_latest_updated_nav_sync_run()
        today = datetime.now(ZoneInfo(TIMEZONE)).date()
        if (
            latest_updated_run is not None
            and latest_updated_run.finished_at.date() == today
        ):
            _completed_date = today
    except Exception as exc:
        logger.warning("Fund NAV scheduler state could not be restored: {}", exc)
    finally:
        db.close()

    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        _run_scheduled_fund_nav_sync,
        CronTrigger.from_crontab(settings.fund_nav_sync_cron, timezone=TIMEZONE),
        id=JOB_ID,
        name="Fund NAV auto sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Fund NAV auto sync scheduler started: {}", settings.fund_nav_sync_cron)


def stop_fund_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Fund NAV auto sync scheduler stopped.")
    _scheduler = None


def get_fund_scheduler_status() -> dict[str, object]:
    settings = get_settings()
    job = _scheduler.get_job(JOB_ID) if _scheduler is not None else None
    return {
        "enabled": settings.fund_nav_auto_sync_enabled,
        "running": bool(_scheduler is not None and _scheduler.running),
        "cron": settings.fund_nav_sync_cron,
        "timezone": TIMEZONE,
        "next_run_at": job.next_run_time if job and job.next_run_time else None,
        "last_run": _last_run,
    }


def _run_scheduled_fund_nav_sync() -> None:
    global _completed_date, _last_run
    now = datetime.now(ZoneInfo(TIMEZONE))
    if _completed_date == now.date():
        message = "Fund NAV sync skipped because new NAV data was already saved today."
        logger.info(message)
        db = SessionLocal()
        try:
            repository = FundRepository(db)
            _last_run = _save_run(
                repository,
                status="succeeded",
                started_at=now,
                finished_at=now,
                total=0,
                succeeded=0,
                failed=0,
                updated=0,
                skipped=True,
                message=message,
            )
        finally:
            db.close()
        return

    db = SessionLocal()
    repository = FundRepository(db)
    try:
        logger.info("Starting scheduled fund NAV sync.")
        settings = get_settings()
        service = FundService(repository, settings=settings)
        result = service.sync_tracked_navs()
        if result.updated > 0:
            _completed_date = now.date()
        status = "succeeded" if result.failed == 0 else "partial"
        message = (
            f"Fund NAV sync finished: {result.succeeded}/{result.total} succeeded, "
            f"{result.updated} updated, {result.failed} failed."
        )
        logger.info(message)
        _last_run = _save_run(
            repository,
            status=status,
            started_at=now,
            finished_at=datetime.now(ZoneInfo(TIMEZONE)),
            total=result.total,
            succeeded=result.succeeded,
            failed=result.failed,
            updated=result.updated,
            skipped=False,
            message=message,
        )
    except Exception as exc:
        logger.exception("Scheduled fund NAV sync failed: {}", exc)
        repository.rollback()
        _last_run = _save_run(
            repository,
            status="failed",
            started_at=now,
            finished_at=datetime.now(ZoneInfo(TIMEZONE)),
            total=0,
            succeeded=0,
            failed=0,
            updated=0,
            skipped=False,
            message=f"Fund NAV sync failed: {exc}",
        )
    finally:
        db.close()


def _save_run(
    repository: FundRepository,
    *,
    status: str,
    started_at: datetime,
    finished_at: datetime,
    total: int,
    succeeded: int,
    failed: int,
    updated: int,
    skipped: bool,
    message: str,
) -> dict[str, object]:
    run = repository.create_nav_sync_run(
        trigger_type="scheduled",
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        total=total,
        succeeded=succeeded,
        failed=failed,
        updated=updated,
        skipped=skipped,
        message=message,
    )
    repository.commit()
    return _run_to_dict(run)


def _run_to_dict(run: FundNavSyncRunModel) -> dict[str, object]:
    return {
        "id": run.id,
        "trigger_type": run.trigger_type,
        "status": run.status,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "total": run.total,
        "succeeded": run.succeeded,
        "failed": run.failed,
        "updated": run.updated,
        "skipped": run.skipped,
        "message": run.message,
    }
