from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from loguru import logger
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError

from app.api.v1 import system
from app.core.config.settings import Settings
from app.core.database import maintenance, migrations
from app.core.database import session as database
from app.core.database.base import Base
from app.main import create_app


@pytest.fixture
def probe(tmp_path, monkeypatch):
    path = tmp_path / "synthetic.db"
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    # Fixture preparation only. Health requests below may execute SELECT 1 only.
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE fixture_data (value TEXT)"))
        connection.execute(text("INSERT INTO fixture_data VALUES ('unchanged')"))
    gate = maintenance.DatabaseMaintenance()
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(maintenance, "database_maintenance", gate)
    monkeypatch.setattr(system, "database_maintenance", gate)
    settings = Settings.model_construct(
        app_version="1.0.0", app_build_sha="synthetic-revision", app_build_time="synthetic-time",
        app_image_reference="synthetic-image", app_deployment_environment="test",
    )
    monkeypatch.setattr(system, "get_settings", lambda: settings)
    forbidden = Mock(side_effect=AssertionError("Health must not create schema or migrate"))
    monkeypatch.setattr(Base.metadata, "create_all", forbidden)
    monkeypatch.setattr(database, "create_database_schema", forbidden)
    monkeypatch.setattr(migrations, "run_database_migrations", forbidden)
    statements = []

    @event.listens_for(engine, "before_cursor_execute")
    def only_select_one(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)
        if statement != "SELECT 1":
            raise AssertionError("Unexpected health probe SQL")

    records = []
    sink = logger.add(lambda msg: records.append(msg.record.copy()))
    # No lifespan: exercising the actual router/auth/maintenance middleware must not run startup.
    client = TestClient(create_app())
    try:
        yield SimpleNamespace(path=path, engine=engine, gate=gate, client=client,
                              statements=statements, forbidden=forbidden, records=records)
    finally:
        client.close()
        logger.remove(sink)
        engine.dispose()


def check(probe, database_status="ok"):
    response = probe.client.get("/api/v1/system/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["database"] == database_status
    assert payload["data"]["status"] == ("ok" if database_status == "ok" else "degraded")
    return response


def test_healthy_query_is_read_only_and_preserves_metadata(probe):
    before = sha256(probe.path.read_bytes()).hexdigest()
    response = check(probe)
    assert response.json()["data"] == {
        "status": "ok", "database": "ok", "version": "1.0.0",
        "git_sha": "synthetic-revision", "git_commit": "synthetic-revision",
        "build_time": "synthetic-time", "image": "synthetic-image", "environment": "test",
    }
    assert probe.statements == ["SELECT 1"]
    assert probe.engine.pool.checkedout() == 0
    assert sha256(probe.path.read_bytes()).hexdigest() == before
    assert sorted(p.name for p in probe.path.parent.iterdir()) == ["synthetic.db"]
    probe.forbidden.assert_not_called()


@pytest.mark.parametrize("stage", ["connect", "query"])
def test_failure_is_sanitized_and_connection_released(probe, monkeypatch, stage):
    sentinel = "synthetic-secret-path-and-credential"
    failure = OperationalError("SELECT 1", {}, RuntimeError(sentinel))
    if stage == "connect":
        monkeypatch.setattr(probe.engine, "connect", Mock(side_effect=failure))
    else:
        @event.listens_for(probe.engine, "before_cursor_execute")
        def fail(*args):
            raise failure

    response = check(probe, "error")
    assert sentinel not in response.text
    assert sentinel not in repr(probe.records)
    assert str(probe.path) not in response.text
    assert probe.engine.pool.checkedout() == 0
    assert probe.gate.status()["active_operations"] == 0
    assert any(r["extra"].get("reason") == "DB_PROBE_FAILED" for r in probe.records)
    probe.forbidden.assert_not_called()


def test_anonymous_health_and_protected_routes_unchanged(probe):
    assert not probe.client.cookies
    check(probe)
    assert probe.client.get("/api/v1/system/build-info").status_code == 401


@pytest.mark.parametrize("phase", ["PREPARING", "MAINTENANCE", "RESTORING", "MIGRATING", "ROLLING_BACK", "RECOVERY_REQUIRED"])
def test_maintenance_never_opens_database(probe, monkeypatch, phase):
    probe.gate.begin_restore()
    probe.gate.transition(phase)
    probe.engine.dispose()
    connect = Mock(side_effect=AssertionError("No connection permitted during maintenance"))
    monkeypatch.setattr(probe.engine, "connect", connect)
    check(probe, "maintenance")
    connect.assert_not_called()
    assert probe.statements == []
    probe.forbidden.assert_not_called()


def test_disposed_engine_reconnects_normally(probe):
    previous_pool = probe.engine.pool
    probe.engine.dispose()
    check(probe)
    assert probe.engine.pool is not previous_pool
    assert probe.engine.pool.checkedout() == 0


@pytest.mark.parametrize("phase", ["COMPLETED", "ROLLED_BACK"])
def test_restore_or_rollback_reopens_health(probe, phase):
    probe.gate.begin_restore()
    probe.gate.drain()
    probe.engine.dispose()
    check(probe, "maintenance")
    probe.gate.finish(phase, usable=True)
    check(probe)


def test_fail_closed_restore_stays_observable(probe):
    probe.gate.begin_restore()
    probe.gate.finish("FAILED", usable=False)
    check(probe, "maintenance")
    assert probe.statements == []


def test_database_recovery_needs_no_restart(probe, monkeypatch):
    connect = probe.engine.connect
    monkeypatch.setattr(probe.engine, "connect", Mock(side_effect=OperationalError("", {}, RuntimeError("synthetic"))))
    check(probe, "error")
    monkeypatch.setattr(probe.engine, "connect", connect)
    check(probe)


def test_missing_database_is_not_created(probe):
    probe.engine.dispose()
    probe.path.unlink()  # Only the fixture's disposable file.
    check(probe, "error")
    assert not probe.path.exists()
    assert probe.statements == []


def test_empty_existing_schema_is_connectivity_not_integrity(probe):
    probe.engine.dispose()
    probe.path.write_bytes(b"")  # Synthetic empty DB, not application data.
    check(probe)
    assert probe.path.stat().st_size == 0
    assert probe.statements == ["SELECT 1"]
    probe.forbidden.assert_not_called()


def test_restore_waits_for_inflight_probe(probe):
    entered = Event()
    release = Event()
    drained = Event()

    @event.listens_for(probe.engine, "before_cursor_execute")
    def pause(*args):
        entered.set()
        if not release.wait(5):
            raise AssertionError("Probe was not released")

    with ThreadPoolExecutor(max_workers=2) as workers:
        query = workers.submit(system._database_readiness)
        try:
            assert entered.wait(5)
            probe.gate.begin_restore()

            def drain():
                probe.gate.drain(timeout=5)
                drained.set()

            pending = workers.submit(drain)
            assert not drained.wait(0.05)
            # A second health request is observable, but cannot acquire a DB connection.
            check(probe, "maintenance")
        finally:
            release.set()
        assert query.result(timeout=5) == "ok"
        pending.result(timeout=5)
    assert drained.is_set()
    assert probe.engine.pool.checkedout() == 0


def test_http_success_only_docker_contract_for_failure_and_recovery(probe, monkeypatch):
    # Equivalent to the repository's urlopen probe: body is not inspected, HTTP success is enough.
    connect = probe.engine.connect
    for broken in (False, True, False):
        monkeypatch.setattr(probe.engine, "connect", Mock(side_effect=OperationalError("", {}, RuntimeError())) if broken else connect)
        response = check(probe, "error" if broken else "ok")
        response.raise_for_status()
