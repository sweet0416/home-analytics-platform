import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from hashlib import pbkdf2_hmac
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from alembic.script import ScriptDirectory
from app.core.auth import COOKIE_NAME, create_session
from app.core.backup import restore
from app.core.backup import service as backup_module
from app.core.backup.service import DatabaseBackupService
from app.core.config.settings import Settings
from app.core.database import maintenance, migrations
from app.core.database import session as database
from app.core.database.maintenance import require_recovered_database, restore_marker
from app.core.database.migrations import migration_config, run_database_migrations
from app.main import create_app
from app.shared.exceptions.base import AppError


class TestSettings(Settings):
    __test__ = False

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings
    ):
        return (init_settings,)


@pytest.fixture
def restore_env(tmp_path, monkeypatch):
    path = tmp_path / "live.db"
    backups = tmp_path / "backups"
    backups.mkdir()
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", sessions)
    monkeypatch.setattr(backup_module, "SessionLocal", sessions)
    monkeypatch.setattr(migrations, "engine", engine)
    gate = maintenance.DatabaseMaintenance()
    monkeypatch.setattr(maintenance, "database_maintenance", gate)
    monkeypatch.setattr(restore, "database_maintenance", gate)
    from app.api.v1 import system

    monkeypatch.setattr(system, "database_maintenance", gate)
    settings = TestSettings(
        database_url=f"sqlite:///{path}",
        backup_dir=backups,
        backup_auto_enabled=False,
        fund_nav_auto_sync_enabled=False,
        lottery_dlt_auto_sync_enabled=False,
    )
    monkeypatch.setattr(system, "get_settings", lambda: settings)
    run_database_migrations(target_engine=engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE restore_probe (value TEXT NOT NULL)"))
        connection.execute(text("INSERT INTO restore_probe VALUES ('candidate')"))
    service = DatabaseBackupService(settings)
    source = service.create_sqlite_backup(prune=False)
    with engine.begin() as connection:
        connection.execute(text("UPDATE restore_probe SET value='original'"))
    env = SimpleNamespace(
        path=path,
        backups=backups,
        engine=engine,
        sessions=sessions,
        service=service,
        source=source.file_name,
        gate=gate,
        settings=settings,
    )
    try:
        yield env
    finally:
        engine.dispose()


def read_probe(path: Path) -> str:
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        return connection.execute("SELECT value FROM restore_probe").fetchone()[0]


def perform(env):
    return env.service.restore_sqlite_backup(env.source, env.service.RESTORE_CONFIRMATION)


def audit_record(env):
    return json.loads(next(env.backups.glob("hap_restore_*.json")).read_text())


def authenticated_client(app):
    client = TestClient(app)
    session_id, csrf = create_session("restore-test")
    client.cookies.set(COOKIE_NAME, session_id)
    client.headers["X-CSRF-Token"] = csrf
    return client


def test_restore_validates_head_reopens_engine_and_allows_new_writes(restore_env):
    env = restore_env
    previous_pool = env.engine.pool
    result = perform(env)
    assert result.status == "success"
    assert read_probe(env.path) == "candidate"
    assert read_probe(env.backups / result.safety_backup_file_name) == "original"
    assert env.engine.pool is not previous_pool
    assert not restore_marker(env.path).exists()
    assert not env.gate.status()["maintenance"]
    restore.validate_restored_database(env.path)
    with env.sessions.begin() as session:
        session.execute(text("UPDATE restore_probe SET value='new write'"))
    assert read_probe(env.path) == "new write"
    record = audit_record(env)
    assert record["migration"] == "success" and record["stage"] == "COMPLETED"
    with env.sessions() as session:
        row = session.execute(
            text("SELECT started_at, finished_at, message FROM database_restore_runs")
        ).one()
        assert row[0] and row[1]
        assert json.loads(row[2])["operation_id"] == record["operation_id"]


def test_restore_api_and_backup_listing_remain_compatible(restore_env):
    env = restore_env
    client = authenticated_client(create_app())
    response = client.post(
        f"/api/v1/system/backups/{env.source}/restore",
        json={"file_name": env.source, "confirmation": env.service.RESTORE_CONFIRMATION},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "success"
    assert env.service.list_sqlite_backups().latest_restore.status == "success"
    status = client.get("/api/v1/system/restore-status").json()["data"]
    assert status["result"]["migration"] == "success"
    assert status["maintenance"] is False


def test_bad_confirmation_does_not_enter_maintenance(restore_env):
    env = restore_env
    with pytest.raises(AppError):
        env.service.restore_sqlite_backup(env.source, "incorrect")
    assert env.gate.status()["phase"] == "IDLE"
    assert read_probe(env.path) == "original"


def test_login_logout_and_csrf_remain_available_in_maintenance(restore_env, monkeypatch):
    from app.api.v1 import auth

    salt = bytes(16)
    digest = pbkdf2_hmac("sha256", b"synthetic-restore-password", salt, 600_000)
    settings = TestSettings(
        hap_admin_password_hash=f"pbkdf2_sha256$600000${salt.hex()}${digest.hex()}"
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    create_session("testclient")  # Clear any previous test's failed-login counter.
    restore_env.gate.begin_restore()
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "admin",
            "password": "synthetic-restore-password",
        },
    )
    assert response.status_code == 200
    assert client.get("/api/v1/system/restore-status").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 403
    client.headers["X-CSRF-Token"] = response.json()["data"]["csrf_token"]
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/system/restore-status").status_code == 401


@pytest.mark.parametrize("bad", [b"", b"not a database", b"SQLite format 3\x00broken"])
def test_invalid_source_does_not_replace_database(restore_env, bad):
    env = restore_env
    (env.backups / env.source).write_bytes(bad)
    with pytest.raises(AppError):
        perform(env)
    assert read_probe(env.path) == "original"
    assert not env.gate.status()["maintenance"]
    assert audit_record(env)["migration"] == "not_started"


def test_unrelated_sqlite_database_is_rejected(restore_env):
    env = restore_env
    source = env.backups / "hap_unrelated.db"
    with closing(sqlite3.connect(source)) as connection:
        connection.execute("CREATE TABLE other (id INTEGER)")
    with pytest.raises(AppError, match="SCHEMA_IDENTITY"):
        env.service.restore_sqlite_backup(source.name, env.service.RESTORE_CONFIRMATION)
    assert read_probe(env.path) == "original"


def test_safety_backup_failure_prevents_replacement(restore_env, monkeypatch):
    env = restore_env
    monkeypatch.setattr(env.service, "create_sqlite_backup", Mock(side_effect=OSError("synthetic")))
    with pytest.raises(AppError, match="NO_REPLACEMENT"):
        perform(env)
    assert read_probe(env.path) == "original"
    assert not restore_marker(env.path).exists()
    assert not env.gate.status()["maintenance"]


def test_quick_check_failure_is_rejected(restore_env, monkeypatch):
    env = restore_env
    real_connect = sqlite3.connect

    class CorruptCheck:
        def __init__(self, connection):
            self.connection = connection

        def execute(self, sql):
            if sql == "PRAGMA quick_check":
                return SimpleNamespace(fetchall=lambda: [("synthetic corruption",)])
            return self.connection.execute(sql)

        def close(self):
            self.connection.close()

    def connect(path, *args, **kwargs):
        connection = real_connect(path, *args, **kwargs)
        return CorruptCheck(connection) if env.source in str(path) else connection

    monkeypatch.setattr(restore.sqlite3, "connect", connect)
    with pytest.raises(AppError, match="QUICK_CHECK"):
        perform(env)
    assert read_probe(env.path) == "original"


def test_old_schema_runs_real_migration_to_head(restore_env):
    env = restore_env
    with closing(sqlite3.connect(env.backups / env.source)) as connection:
        connection.execute("DROP INDEX ix_fund_transactions_external_trade")
        for column in (
            "external_source",
            "external_trade_id",
            "external_trade_type",
            "external_business_code",
            "external_status",
            "external_confirm_status",
            "confirm_date",
            "source_updated_at",
        ):
            connection.execute(f"ALTER TABLE fund_transactions DROP COLUMN {column}")
        connection.execute("UPDATE alembic_version SET version_num='20260808_0021'")
        connection.commit()
    perform(env)
    with env.sessions() as session:
        assert session.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            ScriptDirectory.from_config(migration_config()).get_current_head()
        )
        session.execute(text("SELECT external_trade_id FROM fund_transactions LIMIT 1"))
    assert read_probe(env.path) == "candidate"


def test_legacy_unversioned_hap_backup_is_migrated(restore_env):
    env = restore_env
    with closing(sqlite3.connect(env.backups / env.source)) as connection:
        connection.execute("DROP TABLE alembic_version")
    perform(env)
    restore.validate_restored_database(env.path)


def test_unknown_revision_rejected_before_safety_backup(restore_env, monkeypatch):
    env = restore_env
    with closing(sqlite3.connect(env.backups / env.source)) as connection:
        connection.execute("UPDATE alembic_version SET version_num='unknown_revision'")
        connection.commit()
    backup = Mock()
    monkeypatch.setattr(env.service, "create_sqlite_backup", backup)
    with pytest.raises(AppError, match="REVISION"):
        perform(env)
    backup.assert_not_called()
    assert read_probe(env.path) == "original"


def test_atomic_replace_failure_keeps_original(restore_env, monkeypatch):
    env = restore_env
    real_replace = restore.os.replace

    def fail_target(source, target):
        if target == env.path:
            raise PermissionError("synthetic replace failure")
        return real_replace(source, target)

    monkeypatch.setattr(restore.os, "replace", fail_target)
    with pytest.raises(AppError, match="NO_REPLACEMENT"):
        perform(env)
    assert read_probe(env.path) == "original"
    assert not restore_marker(env.path).exists()


def test_interruption_after_replacement_does_not_resume(restore_env, monkeypatch):
    env = restore_env
    monkeypatch.setattr(restore, "run_database_migrations", Mock(side_effect=SystemExit))
    with pytest.raises(SystemExit):
        perform(env)
    assert env.gate.status()["maintenance"] is True
    assert restore_marker(env.path).exists()
    assert audit_record(env)["stage"] == "MIGRATING"


def test_audit_failure_after_replace_still_attempts_rollback(restore_env, monkeypatch):
    env = restore_env
    original = restore._save_audit

    def audit(path, record):
        if record["stage"] in {"MIGRATING", "ROLLING_BACK"}:
            raise OSError("synthetic audit disk error")
        original(path, record)

    monkeypatch.setattr(restore, "_save_audit", audit)
    with pytest.raises(AppError, match="ROLLBACK_SUCCEEDED"):
        perform(env)
    assert read_probe(env.path) == "original"
    assert not env.gate.status()["maintenance"]
    assert audit_record(env)["rollback"] == "success"


@pytest.mark.parametrize("failure", ["migration", "validation"])
def test_post_replace_failure_rolls_back_readable_database(restore_env, monkeypatch, failure):
    env = restore_env
    name = "run_database_migrations" if failure == "migration" else "validate_restored_database"
    original = getattr(restore, name)
    calls = []

    def fail_once(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("synthetic stage failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(restore, name, fail_once)
    with pytest.raises(AppError, match="ROLLBACK_SUCCEEDED") as caught:
        perform(env)
    assert caught.value.details["rollback"] == "success"
    assert read_probe(env.path) == "original"
    assert not env.gate.status()["maintenance"]
    assert not restore_marker(env.path).exists()
    assert audit_record(env)["rollback"] == "success"
    with env.sessions.begin() as session:
        session.execute(text("UPDATE restore_probe SET value='after rollback'"))
    assert read_probe(env.path) == "after rollback"


def test_rollback_failure_stays_closed_and_blocks_restart(restore_env, monkeypatch):
    env = restore_env
    monkeypatch.setattr(
        restore, "run_database_migrations", Mock(side_effect=RuntimeError("synthetic"))
    )
    with pytest.raises(AppError, match="ROLLBACK_FAILED") as caught:
        perform(env)
    assert caught.value.details["maintenance"] is True
    assert env.gate.status()["maintenance"] is True
    assert audit_record(env)["rollback"] == "failed"
    with pytest.raises(RuntimeError, match="RECOVERY_REQUIRED"):
        require_recovered_database(env.path)
    with pytest.raises(RuntimeError, match="RECOVERY_REQUIRED"):
        run_database_migrations()
    with pytest.raises(AppError, match="RECOVERY_REQUIRED"):
        perform(env)
    client = authenticated_client(create_app())
    assert client.get("/api/v1/fund/positions").status_code == 503
    assert client.get("/api/v1/system/restore-status").json()["data"]["maintenance"] is True


@pytest.mark.parametrize("location", ["source", "target"])
@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_sidecars_are_preserved_and_restore_rejected(restore_env, location, suffix):
    env = restore_env
    path = env.path if location == "target" else env.backups / env.source
    sidecar = Path(str(path) + suffix)
    sidecar.write_bytes(b"synthetic-sidecar-evidence")
    before = env.path.read_bytes()
    with pytest.raises(AppError, match="SIDECARS"):
        perform(env)
    assert sidecar.read_bytes() == b"synthetic-sidecar-evidence"
    assert env.path.read_bytes() == before


def test_wal_mode_without_sidecars_is_rejected(restore_env):
    env = restore_env
    path = env.backups / env.source
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
    with pytest.raises(AppError, match="WAL_UNSUPPORTED"):
        perform(env)
    assert read_probe(env.path) == "original"


def test_untracked_active_connection_aborts_before_replace(restore_env):
    env = restore_env
    with env.engine.connect():
        with pytest.raises(AppError, match="CONNECTIONS_STILL_ACTIVE"):
            perform(env)
    assert read_probe(env.path) == "original"


def test_restore_blocks_requests_and_machine_writes_but_keeps_status(restore_env, monkeypatch):
    env = restore_env
    entered, release = Event(), Event()
    original = restore.run_database_migrations

    def paused_migration(**kwargs):
        entered.set()
        assert release.wait(5)
        return original(**kwargs)

    monkeypatch.setattr(restore, "run_database_migrations", paused_migration)
    app = create_app()
    client = authenticated_client(app)
    with ThreadPoolExecutor() as executor:
        future = executor.submit(perform, env)
        try:
            assert entered.wait(5)
            assert client.post("/api/v1/fund/positions", json={}).status_code == 503
            assert client.get("/api/v1/fund/positions").status_code == 503
            assert client.get("/api/v1/system/health").status_code == 200
            response = client.get("/api/v1/system/restore-status")
            assert response.status_code == 200
            assert response.json()["data"]["phase"] == "MIGRATING"
            with pytest.raises(AppError) as caught:
                perform(env)
            assert caught.value.status_code == 409
            machine = TestClient(app)
            assert (
                machine.post("/api/v1/fund/integrations/ttskill/nav-info", json={}).status_code
                == 503
            )
            assert machine.get("/api/v1/system/restore-status").status_code == 401
        finally:
            release.set()
        assert future.result(timeout=10).status == "success"


@pytest.mark.parametrize("background", [False, True])
def test_waits_for_inflight_request_and_background_cleanup(restore_env, monkeypatch, background):
    env = restore_env
    entered, release, restore_waiting = Event(), Event(), Event()
    app = create_app()

    def write_slowly():
        with env.sessions.begin() as session:
            session.execute(text("UPDATE restore_probe SET value='drained writer'"))
            entered.set()
            assert release.wait(5)

    @app.post("/api/v1/test-slow")
    def slow_request(tasks: BackgroundTasks):
        if background:
            tasks.add_task(write_slowly)
        else:
            write_slowly()
        return {"ok": True}

    original = env.gate.drain

    def drain():
        restore_waiting.set()
        original()

    monkeypatch.setattr(env.gate, "drain", drain)
    client = authenticated_client(app)
    with ThreadPoolExecutor() as executor:
        writer = executor.submit(client.post, "/api/v1/test-slow")
        assert entered.wait(5)
        operation = executor.submit(perform, env)
        try:
            assert restore_waiting.wait(5)
            assert env.gate.status()["active_operations"] == 1
            assert not operation.done()
        finally:
            release.set()
        assert writer.result(timeout=10).status_code == 200
        result = operation.result(timeout=10)
    assert read_probe(env.backups / result.safety_backup_file_name) == "drained writer"


def test_all_writing_schedulers_skip_during_maintenance(restore_env, monkeypatch):
    from app.core.backup import scheduler as backup
    from app.core.infrastructure_health import scheduler as health
    from app.plugins.fund.jobs import scheduler as fund
    from app.plugins.lottery.jobs import scheduler as lottery

    env = restore_env
    env.gate.begin_restore()
    for module, name in [
        (backup, "_run_scheduled_backup"),
        (health, "_run_scheduled_health_check"),
        (fund, "_run_scheduled_fund_nav_sync"),
        (lottery, "_run_scheduled_dlt_sync"),
    ]:
        settings = Mock(side_effect=AssertionError("a guarded job must not start"))
        monkeypatch.setattr(module, "get_settings", settings)
        assert getattr(module, name)() is None
        settings.assert_not_called()


def test_drain_timeout_preserves_database_and_reopens_gate(restore_env, monkeypatch):
    env = restore_env
    started, release = Event(), Event()

    def active():
        with env.gate.activity() as admitted:
            assert admitted
            started.set()
            assert release.wait(5)

    original = env.gate.drain
    monkeypatch.setattr(env.gate, "drain", lambda: original(timeout=0.01))
    with ThreadPoolExecutor() as executor:
        future = executor.submit(active)
        try:
            assert started.wait(5)
            with pytest.raises(AppError, match="RESTORE_BUSY"):
                perform(env)
        finally:
            release.set()
        future.result(timeout=5)
    assert read_probe(env.path) == "original"
    assert not env.gate.status()["maintenance"]
