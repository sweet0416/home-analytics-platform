"""Quiesced SQLite restore. Only the in-process single-worker writer set is supported."""

import json
import os
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import select, text

from alembic.script import ScriptDirectory
from app.core.backup.repository import DatabaseRestoreRunRepository
from app.core.backup.schemas import DatabaseRestoreRead
from app.core.database import session as database
from app.core.database.base import Base
from app.core.database.maintenance import database_maintenance, restore_marker
from app.core.database.migrations import migration_config, run_database_migrations
from app.core.time import utcnow
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode

if TYPE_CHECKING:
    from app.core.backup.service import DatabaseBackupService


def _reject(message: str) -> AppError:
    return AppError(ErrorCode.validation_error, message, 400)


def _no_sidecars(path: Path) -> None:
    # No automatic checkpoint or unlink: preserve evidence and reject unsupported WAL/hot journals.
    if any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise _reject("RESTORE_SIDECARS_PRESENT: offline recovery is required")


def validate_sqlite(path: Path) -> None:
    _no_sidecars(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise _reject("RESTORE_INVALID_FILE")
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            if connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal":
                raise _reject("RESTORE_WAL_UNSUPPORTED: offline recovery is required")
            if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                raise _reject("RESTORE_QUICK_CHECK_FAILED")
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if not {"funds", "fund_positions", "lottery_games", "lottery_draws"} <= tables:
                raise _reject("RESTORE_SCHEMA_IDENTITY_INVALID")
            if "alembic_version" in tables:
                revisions = connection.execute("SELECT version_num FROM alembic_version").fetchall()
                if len(revisions) != 1:
                    raise _reject("RESTORE_REVISION_INVALID")
                script = ScriptDirectory.from_config(migration_config())
                if script.get_revision(revisions[0][0]) is None:
                    raise _reject("RESTORE_REVISION_INVALID")
    except AppError:
        raise
    except Exception as exc:
        raise _reject("RESTORE_INVALID_SQLITE_OR_REVISION") from exc


def _dispose_engine() -> None:
    checkedout = getattr(database.engine.pool, "checkedout", None)
    if checkedout is None or checkedout() != 0:
        raise AppError(ErrorCode.conflict, "RESTORE_CONNECTIONS_STILL_ACTIVE", 409)
    database.engine.dispose()


def validate_restored_database(path: Path) -> None:
    validate_sqlite(path)
    head = ScriptDirectory.from_config(migration_config()).get_current_head()
    if database.SessionLocal.kw.get("bind") is not database.engine:
        raise RuntimeError("RESTORE_SESSION_BIND_MISMATCH")
    with database.SessionLocal() as session:
        if session.execute(text("SELECT version_num FROM alembic_version")).scalars().all() != [
            head
        ]:
            raise RuntimeError("RESTORE_REVISION_NOT_HEAD")
        # Exercise mapped columns, not just table names, through a fresh application session.
        for table in Base.metadata.sorted_tables:
            session.execute(select(table).limit(1)).first()


def _copy_candidate(source: Path, target: Path) -> None:
    with source.open("rb") as incoming, target.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    validate_sqlite(target)


def _save_audit(path: Path, record: dict[str, str]) -> None:
    temporary = path.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _record_history(record: dict[str, str]) -> None:
    with database.SessionLocal() as session:
        DatabaseRestoreRunRepository(session).record_run(
            source_file_name=record["source"],
            safety_backup_file_name=record["safety_backup"],
            confirmation="matched",
            status=record["status"],
            message=json.dumps(record),
            started_at=datetime.fromisoformat(record["started_at"]),
            finished_at=datetime.fromisoformat(record["finished_at"]),
        )


def restore_database(service: "DatabaseBackupService", file_name: str) -> DatabaseRestoreRead:
    # Resolve only a validated backup name before publishing an operation identity.
    source = service.get_sqlite_backup_path(file_name)
    target = service._get_sqlite_database_path()
    if target.is_symlink():
        raise _reject("RESTORE_INVALID_TARGET")
    target = target.resolve()
    if (
        database.engine.url.get_backend_name() != "sqlite"
        or not database.engine.url.database
        or Path(database.engine.url.database).resolve() != target
        or database.SessionLocal.kw.get("bind") is not database.engine
    ):
        raise _reject("RESTORE_DATABASE_BIND_MISMATCH")
    if source.is_symlink() or source.resolve().parent != service._settings.backup_dir.resolve():
        raise _reject("RESTORE_INVALID_FILE")
    if source.samefile(target):
        raise _reject("RESTORE_SOURCE_IS_LIVE_DATABASE")

    operation_id = database_maintenance.begin_restore()
    record = {
        "operation_id": operation_id,
        "source": source.name,
        "safety_backup": "",
        "started_at": utcnow().isoformat(),
        "finished_at": "",
        "status": "running",
        "stage": "PREPARING",
        "migration": "not_started",
        "rollback": "not_needed",
        "failure_stage": "",
        "error_class": "",
    }
    audit = service._settings.backup_dir / f"hap_restore_{operation_id}.json"
    staging = target.with_name(f"{target.name}.restore-{operation_id}.tmp")
    marker = restore_marker(target)
    replaced = False
    marker_owned = False
    usable = True
    safety_path: Path | None = None

    def stage(value: str) -> None:
        record["stage"] = value
        database_maintenance.transition(value)
        _save_audit(audit, record)
        logger.info("database_restore operation_id={} stage={}", operation_id, value)

    try:
        stage("PREPARING")
        database_maintenance.drain()
        if marker.exists():
            usable = False
            raise RuntimeError("RESTORE_RECOVERY_REQUIRED")
        stage("MAINTENANCE")
        validate_sqlite(source)
        # Check before dispose as well: closing the last WAL connection can checkpoint/unlink sidecars.
        validate_sqlite(target)
        _dispose_engine()
        stage("SAFETY_BACKUP")
        safety = service.create_sqlite_backup(label="pre_restore", prune=False)
        safety_path = service.get_sqlite_backup_path(safety.file_name)
        record["safety_backup"] = safety.file_name
        validate_sqlite(safety_path)
        stage("STAGING")
        _copy_candidate(source, staging)
        with marker.open("x", encoding="ascii") as stream:
            marker_owned = True
            stream.write(operation_id)
            stream.flush()
            os.fsync(stream.fileno())
        stage("RESTORING")
        _no_sidecars(target)
        os.replace(staging, target)
        replaced = True
        usable = False
        record["migration"] = "running"
        stage("MIGRATING")
        run_database_migrations(target_engine=database.engine)
        record["migration"] = "success"
        stage("VALIDATING")
        validate_restored_database(target)
        stage("RECORDING")
        record.update(status="success", finished_at=utcnow().isoformat())
        _record_history(record)
        stage("COMPLETED")
        marker.unlink()
        marker_owned = False
        usable = True
        return DatabaseRestoreRead(
            source_file_name=source.name,
            safety_backup_file_name=safety.file_name,
            status="success",
            message="RESTORE_SUCCESS: migrations and database validation passed.",
            restored_at=datetime.fromisoformat(record["started_at"]),
        )
    except Exception as exc:
        record["failure_stage"] = record["stage"]
        record["error_class"] = type(exc).__name__
        if record["migration"] == "running":
            record["migration"] = "failed"
        if replaced:
            usable = False
            record["rollback"] = "running"
            try:
                try:
                    stage("ROLLING_BACK")
                except Exception:
                    logger.error(
                        "database_restore operation_id={} rollback_audit_write=failed", operation_id
                    )
                _no_sidecars(target)
                _dispose_engine()
                if safety_path is None:
                    raise RuntimeError("RESTORE_SAFETY_BACKUP_MISSING")
                validate_sqlite(safety_path)
                record["rollback_stage"] = "COPYING"
                _copy_candidate(safety_path, staging)
                record["rollback_stage"] = "REPLACING"
                os.replace(staging, target)
                record["rollback_stage"] = "MIGRATING"
                run_database_migrations(target_engine=database.engine)
                record["rollback_stage"] = "VALIDATING"
                validate_restored_database(target)
                record["rollback"] = "success"
                record["rollback_stage"] = "COMPLETED"
                usable = True
            except Exception as rollback_exc:
                record["rollback"] = "failed"
                record["rollback_error_class"] = type(rollback_exc).__name__
        record.update(status="failed", stage="FAILED", finished_at=utcnow().isoformat())
        try:
            _save_audit(audit, record)
            if usable:
                if replaced:
                    _record_history(record)
                if marker_owned:
                    marker.unlink()
                    marker_owned = False
        except Exception as audit_exc:
            # The external journal/marker survives database replacement and failed rollback.
            logger.error(
                "database_restore operation_id={} audit_error_class={}",
                operation_id,
                type(audit_exc).__name__,
            )
            if marker_owned:
                usable = False
        logger.error(
            "database_restore operation_id={} failure_stage={} error_class={} rollback={} usable={}",
            operation_id,
            record["failure_stage"],
            record["error_class"],
            record["rollback"],
            usable,
        )
        if isinstance(exc, AppError) and not replaced and usable:
            raise
        outcome = (
            "ROLLBACK_SUCCEEDED"
            if record["rollback"] == "success"
            else ("ROLLBACK_FAILED" if record["rollback"] == "failed" else "NO_REPLACEMENT")
        )
        raise AppError(
            ErrorCode.internal_error,
            f"RESTORE_FAILED / {outcome}. "
            + (
                "Database is usable."
                if usable
                else "Maintenance remains active; manual recovery required."
            ),
            500,
            details={
                "operation_id": operation_id,
                "failure_stage": record["failure_stage"],
                "migration": record["migration"],
                "rollback": record["rollback"],
                "maintenance": not usable,
            },
        ) from None
    finally:
        try:
            staging.unlink(missing_ok=True)
        except OSError:
            logger.warning(
                "database_restore operation_id={} temporary_cleanup=failed", operation_id
            )
        database_maintenance.finish(
            record["stage"],
            usable=usable,
            result={
                key: record[key] for key in ("status", "migration", "rollback", "failure_stage")
            },
        )
