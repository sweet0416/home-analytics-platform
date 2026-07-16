from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.core.backup.remote import GithubBackupClient, RemoteBackupResult
from app.core.backup.service import DatabaseBackupService
from app.core.config.settings import get_settings

_scheduler: BackgroundScheduler | None = None
_last_run_at: datetime | None = None
_last_status: str | None = None
_last_message: str | None = None
_last_backup_file_name: str | None = None
_last_remote_status: str | None = None
_last_remote_message: str | None = None
_last_remote_asset_name: str | None = None
_last_remote_uploaded_at: datetime | None = None


def start_backup_scheduler() -> None:
    settings = get_settings()
    if not settings.backup_auto_enabled:
        logger.info("Database auto backup is disabled.")
        return

    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.info("Database auto backup scheduler is already running.")
        return

    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        _run_scheduled_backup,
        CronTrigger.from_crontab(settings.backup_cron, timezone="Asia/Shanghai"),
        id="database_auto_backup",
        name="Database auto backup",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Database auto backup scheduler started: {}", settings.backup_cron)


def stop_backup_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return

    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Database auto backup scheduler stopped.")
    _scheduler = None


def get_backup_scheduler_status() -> dict[str, object]:
    settings = get_settings()
    job = _scheduler.get_job("database_auto_backup") if _scheduler is not None else None
    remote_status = GithubBackupClient(settings=settings).status()
    return {
        "enabled": settings.backup_auto_enabled,
        "running": bool(_scheduler is not None and _scheduler.running),
        "cron": settings.backup_cron,
        "timezone": "Asia/Shanghai",
        "next_run_at": job.next_run_time.isoformat() if job and job.next_run_time else None,
        "last_run_at": _last_run_at.isoformat() if _last_run_at else None,
        "last_status": _last_status,
        "last_message": _last_message,
        "last_backup_file_name": _last_backup_file_name,
        "remote": {
            **remote_status,
            "last_status": _last_remote_status,
            "last_message": _last_remote_message,
            "last_asset_name": _last_remote_asset_name,
            "last_uploaded_at": (
                _last_remote_uploaded_at.isoformat() if _last_remote_uploaded_at else None
            ),
        },
    }


def _run_scheduled_backup() -> None:
    global _last_backup_file_name, _last_message, _last_run_at, _last_status
    _last_run_at = datetime.now()
    try:
        settings = get_settings()
        service = DatabaseBackupService(settings=settings)
        backup = service.create_sqlite_backup()
        _last_backup_file_name = backup.file_name
        _last_status = "success"
        _last_message = f"Backup created: {backup.file_name}"
        logger.info("Scheduled database backup finished: {}", backup.file_name)
        backup_path = service.get_sqlite_backup_path(backup.file_name)
        try:
            _record_remote_backup_result(
                GithubBackupClient(settings=settings).upload_encrypted_backup(backup_path)
            )
        except Exception as exc:
            _record_remote_backup_failure(exc)
            logger.exception("Encrypted GitHub backup upload failed: {}", exc)
    except Exception as exc:
        _last_backup_file_name = None
        _last_status = "failed"
        _last_message = str(exc)
        logger.exception("Scheduled database backup failed: {}", exc)


def _record_remote_backup_result(result: RemoteBackupResult) -> None:
    global _last_remote_asset_name, _last_remote_message, _last_remote_status
    global _last_remote_uploaded_at
    _last_remote_status = result.status
    _last_remote_message = result.message
    _last_remote_asset_name = result.asset_name
    _last_remote_uploaded_at = result.uploaded_at


def _record_remote_backup_failure(exc: Exception) -> None:
    global _last_remote_asset_name, _last_remote_message, _last_remote_status
    global _last_remote_uploaded_at
    _last_remote_status = "failed"
    _last_remote_message = str(exc)
    _last_remote_asset_name = None
    _last_remote_uploaded_at = None
