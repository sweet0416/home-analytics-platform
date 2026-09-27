"""Verify a HAP backup on an isolated copy; never migrate the supplied file."""

import hashlib
import json
import os
import shutil
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

CORE_TABLES = (
    "funds",
    "fund_positions",
    "fund_transactions",
    "fund_nav_records",
    "fund_daily_report_snapshots",
    "lottery_games",
    "lottery_draws",
    "notification_delivery_runs",
    "database_backup_runs",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inspect(path: Path) -> dict[str, object]:
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        connection.execute("PRAGMA query_only=ON")
        journal = connection.execute("PRAGMA journal_mode").fetchone()[0]
        quick = connection.execute("PRAGMA quick_check").fetchall()
        integrity = connection.execute("PRAGMA integrity_check").fetchall()
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        tables = {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        revision = (
            connection.execute("SELECT version_num FROM alembic_version").fetchall()
            if "alembic_version" in tables else []
        )
        counts = {
            table: connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            for table in CORE_TABLES if table in tables
        }
        if quick != [("ok",)] or integrity != [("ok",)]:
            raise ValueError("SQLITE_INTEGRITY_FAILED")
        if foreign_keys:
            raise ValueError("FOREIGN_KEY_CHECK_FAILED")
        return {
            "quick_check": "ok",
            "integrity_check": "ok",
            "foreign_key_check": "ok",
            "journal_mode": journal,
            "user_version": connection.execute("PRAGMA user_version").fetchone()[0],
            "alembic_revision": revision[0][0] if len(revision) == 1 else "UNVERSIONED",
            "counts": counts,
        }


def verify_backup(source: Path) -> dict[str, object]:
    source = source.absolute()
    if source.is_symlink() or not source.is_file() or source.stat().st_size == 0:
        raise ValueError("INVALID_BACKUP_FILE")
    if any(Path(str(source) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise ValueError("BACKUP_SIDECARS_PRESENT")
    source_hash = _sha256(source)
    with TemporaryDirectory(prefix="hap-recovery-") as temporary:
        workspace = Path(temporary)
        copy = workspace / "candidate.db"
        shutil.copyfile(source, copy)
        copy_hash = _sha256(copy)
        if copy_hash != source_hash or _sha256(source) != source_hash:
            raise ValueError("BACKUP_CHANGED_DURING_COPY")
        result: dict[str, object] = {
            "size_bytes": source.stat().st_size,
            "source_sha256": source_hash,
            "copy_sha256": copy_hash,
        }
        with copy.open("rb") as stream:
            header = stream.read(16)
        if header != b"SQLite format 3\x00":
            raise ValueError("INVALID_SQLITE_HEADER")
        result.update(_inspect(copy))

        # Imports and migration run only after moving to a clean disposable cwd.
        # The application's default Settings must never bind to caller .env or DB.
        previous_cwd = Path.cwd()
        previous_env = os.environ.copy()
        try:
            os.chdir(workspace)
            from app.core.config.settings import Settings

            fields = {name.casefold() for name in Settings.model_fields}
            for key in tuple(os.environ):
                if key.casefold() in fields:
                    del os.environ[key]
            from sqlalchemy import create_engine, select, text
            from sqlalchemy.orm import Session

            from alembic.script import ScriptDirectory
            from app.api.v1 import system
            from app.core.backup.restore import validate_sqlite
            from app.core.database.base import Base
            from app.core.database.migrations import migration_config, run_database_migrations

            validate_sqlite(copy)
            engine = create_engine(f"sqlite:///{copy}", connect_args={"check_same_thread": False})
            try:
                head = ScriptDirectory.from_config(migration_config()).get_current_head()
                run_database_migrations(target_engine=engine)
                with Session(engine) as session:
                    if session.execute(text("SELECT version_num FROM alembic_version")).scalar_one() != head:
                        raise ValueError("MIGRATION_NOT_AT_HEAD")
                    session.execute(text("SELECT 1")).scalar_one()
                    for table in Base.metadata.sorted_tables:
                        session.execute(select(table).limit(1)).first()
                original_engine = system.database.engine
                try:
                    system.database.engine = engine
                    if system._database_readiness() != "ok":
                        raise ValueError("HEALTH_PROBE_FAILED")
                finally:
                    system.database.engine = original_engine
                result.update({"alembic_after": head, "app_read": "ok", "health_probe": "ok"})
            finally:
                engine.dispose()
            final = _inspect(copy)
            result["final_quick_check"] = final["quick_check"]
            if _sha256(source) != source_hash:
                raise ValueError("BACKUP_CHANGED_DURING_VERIFICATION")
            result["recovery_status"] = "RECOVERY_VERIFIED"
            return result
        finally:
            os.environ.clear()
            os.environ.update(previous_env)
            os.chdir(previous_cwd)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.verify_backup BACKUP.db", file=sys.stderr)
        raise SystemExit(2)
    try:
        print(json.dumps(verify_backup(Path(sys.argv[1])), sort_keys=True))
    except Exception as exc:
        safe_codes = {
            "INVALID_BACKUP_FILE", "BACKUP_SIDECARS_PRESENT", "BACKUP_CHANGED_DURING_COPY",
            "INVALID_SQLITE_HEADER", "SQLITE_INTEGRITY_FAILED", "FOREIGN_KEY_CHECK_FAILED",
            "MIGRATION_NOT_AT_HEAD", "HEALTH_PROBE_FAILED", "BACKUP_CHANGED_DURING_VERIFICATION",
        }
        reason = str(exc) if type(exc) is ValueError and str(exc) in safe_codes else type(exc).__name__
        print(f"RECOVERY_UNVERIFIED: {reason}", file=sys.stderr)
        raise SystemExit(1) from None
