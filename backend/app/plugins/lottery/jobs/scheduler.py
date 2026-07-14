from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.core.config.settings import get_settings
from app.core.database.session import SessionLocal
from app.plugins.lottery.application.services import LotteryService
from app.plugins.lottery.domain.sync import DrawSyncCommand

_scheduler: BackgroundScheduler | None = None


def start_lottery_scheduler() -> None:
    settings = get_settings()
    if not settings.lottery_dlt_auto_sync_enabled:
        logger.info("DLT auto sync is disabled.")
        return

    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.info("DLT auto sync scheduler is already running.")
        return

    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        _run_scheduled_dlt_sync,
        CronTrigger.from_crontab(settings.lottery_dlt_sync_cron, timezone="Asia/Shanghai"),
        id="lottery_dlt_auto_sync",
        name="DLT draw auto sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("DLT auto sync scheduler started: {}", settings.lottery_dlt_sync_cron)


def _run_scheduled_dlt_sync() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        logger.info("Starting scheduled DLT draw sync.")
        service = LotteryService(db)
        result = service.sync_draws(
            DrawSyncCommand(
                sync_type="scheduled",
                page=1,
                page_size=settings.lottery_dlt_sync_page_size,
                force=False,
            )
        )
        logger.info("Scheduled DLT draw sync finished: {}", result)
    except Exception as exc:
        logger.exception("Scheduled DLT draw sync failed: {}", exc)
    finally:
        db.close()
