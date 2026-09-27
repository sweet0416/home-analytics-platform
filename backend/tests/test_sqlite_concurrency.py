"""Disposable-file experiments; timings are evidence, not performance promises.

Run with pytest -s to retain SQLITE_EVIDENCE JSON lines. Both journal modes use
the application dialect's connection arguments; only the experiment sets WAL.
No provider/network calls, production database, or caller Settings are used.
"""

import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, nullcontext
from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from threading import Barrier, Event, RLock
from time import perf_counter, sleep
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

from app.core.auth import COOKIE_NAME, create_session
from app.core.backup.service import DatabaseBackupService
from app.core.config.settings import Settings, get_settings
from app.core.database import maintenance
from app.core.database import session as database
from app.core.database.base import Base
from app.core.notification.models import NotificationDeliveryRunModel
from app.main import create_app
from app.plugins.fund.application.services import FundService
from app.plugins.fund.infrastructure.persistence.models import (
    FundModel,
    FundNavRecordModel,
    FundPositionModel,
)
from app.plugins.fund.infrastructure.persistence.repositories import FundRepository
from app.plugins.fund.jobs import scheduler as fund_scheduler
from app.plugins.lottery.application import services as lottery_services
from app.plugins.lottery.infrastructure.persistence.models import LotterySyncRunModel
from app.plugins.lottery.jobs import scheduler as lottery_scheduler


class SyntheticSettings(Settings):
    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings
    ):
        return (init_settings,)


def evidence(case, env, **values):
    print("SQLITE_EVIDENCE " + json.dumps({"case": case, "mode": env.mode, **values}))


@pytest.fixture(params=["delete", "wal"])
def sqlite_env(request, tmp_path, monkeypatch):
    path = tmp_path / "experiment.db"
    url = database.engine.url.set(database=str(path))
    assert url.get_backend_name() == "sqlite"
    _, arguments = database.engine.dialect.create_connect_args(url)
    engine = create_engine(url, connect_args=arguments)
    with engine.connect() as connection:
        # Persistent mode changes are strictly limited to this pytest-created file.
        if request.param == "wal":
            assert connection.exec_driver_sql("PRAGMA journal_mode=WAL").scalar() == "wal"
        assert connection.exec_driver_sql("PRAGMA journal_mode").scalar() == request.param
    database.create_database_schema(engine)
    sessions = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    gate = maintenance.DatabaseMaintenance()
    monkeypatch.setattr(maintenance, "database_maintenance", gate)
    settings = SyntheticSettings(database_url=str(url), backup_dir=tmp_path / "backups")
    env = SimpleNamespace(
        path=path, mode=request.param, engine=engine, sessions=sessions,
        gate=gate, settings=settings, arguments=arguments,
    )
    yield env
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA quick_check").fetchall() == [("ok",)]
    engine.dispose()


def fund_write(session, code):
    return FundRepository(session).upsert_fund(
        code=code, name="Synthetic fund", fund_type="test", source="concurrency-test",
    )


def count(env, model=FundModel):
    with env.sessions() as session:
        return session.scalar(select(func.count()).select_from(model))


def test_connection_defaults_and_reconnection(sqlite_env):
    env = sqlite_env
    with env.engine.connect() as first, env.engine.connect() as second:
        raw = first.connection.driver_connection
        values = {key: first.exec_driver_sql(f"PRAGMA {key}").scalar() for key in (
            "busy_timeout", "journal_mode", "synchronous", "foreign_keys",
        )}
        assert values == dict(busy_timeout=5000, journal_mode=env.mode,
                              synchronous=2, foreign_keys=0)
        assert second.exec_driver_sql("PRAGMA busy_timeout").scalar() == 5000
        assert env.arguments["check_same_thread"] is False
        assert raw.isolation_level == ""
        assert raw.autocommit == sqlite3.LEGACY_TRANSACTION_CONTROL
        evidence("configuration", env, sqlite=sqlite3.sqlite_version,
                 pool=type(env.engine.pool).__name__, **values,
                 isolation_level=raw.isolation_level, autocommit=raw.autocommit,
                 connect_timeout=env.arguments.get("timeout", 5.0))
    env.engine.dispose()
    with env.engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA journal_mode").scalar() == env.mode
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 0


@pytest.mark.parametrize("parallel,coordinated", [(False, False), (True, False), (True, True)])
def test_short_writer_burst(sqlite_env, parallel, coordinated):
    env = sqlite_env
    mutex = RLock()

    def write(index):
        start = perf_counter()
        with mutex if coordinated else nullcontext():
            # The experimental mutex is BEFORE transaction/read/flush and is reentrant.
            with mutex if coordinated else nullcontext(), env.sessions() as session:
                fund_write(session, f"burst-{index}")
                session.commit()
        return perf_counter() - start

    start = perf_counter()
    if parallel:
        with ThreadPoolExecutor(max_workers=8) as executor:
            waits = list(executor.map(write, range(32)))
    else:
        waits = [write(index) for index in range(32)]
    assert count(env) == 32
    evidence("burst", env, parallel=parallel, coordinated=coordinated,
             lock_errors=0, committed=32, max_wait=max(waits), elapsed=perf_counter()-start)


@pytest.mark.parametrize("hold", [0.25, 4.8, 7.5])
def test_controlled_writer_timeout_and_rollback(sqlite_env, hold):
    env = sqlite_env
    attempted = Event()
    with ThreadPoolExecutor(max_workers=1) as executor, env.sessions() as blocker:
        fund_write(blocker, "long-writer")

        def contender():
            with env.sessions() as session:
                start = perf_counter()
                attempted.set()
                try:
                    fund_write(session, "short-writer")
                    session.commit()
                    return "committed", perf_counter()-start
                except OperationalError as exc:
                    assert "locked" in str(exc).lower()
                    session.rollback()
                    assert not session.in_transaction()
                    return "locked_rolled_back", perf_counter()-start

        pending = executor.submit(contender)
        assert attempted.wait(2)
        held_from = perf_counter()
        if hold == 7.5:
            # Keep the lock until the contender actually times out; do not race a timer.
            result, waited = pending.result(timeout=15)
            sleep(max(0, hold - (perf_counter() - held_from)))
            blocker.commit()
        else:
            sleep(hold)
            blocker.commit()
            result, waited = pending.result(timeout=10)
        actual_hold = perf_counter() - held_from
    # Near 5 s scheduling jitter is reported rather than hidden by a flaky assertion.
    if hold == 0.25:
        assert result == "committed"
    if hold == 7.5:
        assert result == "locked_rolled_back"
    assert count(env) == (2 if result == "committed" else 1)
    with env.sessions() as session:
        fund_write(session, "after-contention")
        session.commit()
    evidence("timeout", env, hold_seconds=hold, actual_hold_seconds=actual_hold,
             result=result, wait_seconds=waited,
             lock_errors=int(result != "committed"), rollback_correct=True)


def test_readers_and_backup_during_uncommitted_writer(sqlite_env):
    env = sqlite_env
    with env.sessions() as session:
        fund_write(session, "committed")
        session.commit()
    with env.sessions() as writer:
        fund_write(writer, "pending")
        with ThreadPoolExecutor(max_workers=5) as executor:
            start = perf_counter()
            readers = list(executor.map(lambda _: count(env), range(4)))
            read_elapsed = perf_counter()-start
            pending = executor.submit(DatabaseBackupService(env.settings).create_sqlite_backup)
            backup = pending.result(timeout=10)
        assert readers == [1] * 4
        with closing(sqlite3.connect(str(env.settings.backup_dir / backup.file_name))) as copy:
            assert copy.execute("PRAGMA quick_check").fetchall() == [("ok",)]
            assert copy.execute("SELECT code FROM funds").fetchall() == [("committed",)]
            assert copy.execute("PRAGMA foreign_key_check").fetchall() == []
        writer.rollback()
    assert count(env) == 1
    evidence("read_backup", env, readers=4, read_seconds=read_elapsed,
             committed_snapshot=True, uncommitted_excluded=True)


def test_read_transaction_commit_pressure_and_checkpoint(sqlite_env):
    env = sqlite_env
    with env.sessions() as session:
        fund_write(session, "initial")
        session.commit()
    with closing(sqlite3.connect(str(env.path))) as reader:
        reader.execute("BEGIN")  # Explicit long-lived read snapshot, unlike legacy SELECT alone.
        assert reader.execute("SELECT count(*) FROM funds").fetchone()[0] == 1
        committing = Event()

        def writer():
            with env.sessions() as session:
                fund_write(session, "new")
                committing.set()
                start = perf_counter()
                session.commit()
                return perf_counter()-start

        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(writer)
            assert committing.wait(2)
            if env.mode == "wal":
                pending.result(timeout=10)  # Must finish without releasing the reader.
            else:
                sleep(0.25)
            completed_during_read = pending.done()
            assert completed_during_read is (env.mode == "wal")
            assert reader.execute("SELECT count(*) FROM funds").fetchone()[0] == 1
            reader.rollback()
            waited = pending.result(timeout=10)
    assert count(env) == 2
    checkpoint = None
    if env.mode == "wal":
        assert Path(str(env.path) + "-wal").exists()
        assert Path(str(env.path) + "-shm").exists()
        with env.engine.connect() as connection:
            checkpoint = tuple(connection.exec_driver_sql("PRAGMA wal_checkpoint(PASSIVE)").one())
        assert checkpoint[0] == 0 and checkpoint[1] == checkpoint[2]
    evidence("reader_commit_pressure", env, commit_seconds=waited,
             completed_during_read=completed_during_read, checkpoint=checkpoint)


def test_http_and_scheduler_persistence_overlap(sqlite_env, monkeypatch):
    env = sqlite_env
    app = create_app()

    def get_db():
        with env.sessions() as session:
            yield session

    app.dependency_overrides[database.get_db] = get_db
    app.dependency_overrides[get_settings] = lambda: env.settings
    client = TestClient(app)  # No lifespan: no live scheduler/provider is started.
    session_id, csrf = create_session("concurrency-test")
    client.cookies.set(COOKIE_NAME, session_id)
    client.headers["X-CSRF-Token"] = csrf
    # Execute the actual guarded scheduled run + repository/history commit path.
    # Its already-completed-day branch is network-free, not a fake SQL writer.
    monkeypatch.setattr(fund_scheduler, "SessionLocal", env.sessions)
    monkeypatch.setattr(fund_scheduler, "_completed_date", fund_scheduler.datetime.now(
        fund_scheduler.ZoneInfo(fund_scheduler.TIMEZONE)).date())
    monkeypatch.setattr(fund_scheduler, "_last_run", None)
    monkeypatch.setattr(lottery_scheduler, "SessionLocal", env.sessions)
    monkeypatch.setattr(lottery_scheduler, "get_settings", lambda: env.settings)
    monkeypatch.setattr(lottery_services, "get_settings", lambda: env.settings)
    monkeypatch.setattr(lottery_services.LotteryService, "_build_dlt_sources",
                        staticmethod(lambda _: [SimpleNamespace(base_url="https://example.invalid")]))
    monkeypatch.setattr(lottery_services.LotteryService, "_fetch_source_page",
                        lambda *args, **kwargs: SimpleNamespace(
                            records=[], raw_metadata={}, source="synthetic",
                            source_url="https://example.invalid"))
    monkeypatch.setattr(lottery_scheduler.DltNotificationService, "notify_sync_result",
                        lambda *args, **kwargs: None)
    # Scheduler exceptions must fail the test, not be swallowed into a fake notification.
    def fail_notification(*args, **kwargs):
        raise AssertionError("Synthetic lottery scheduler failed") from kwargs["exc"]

    monkeypatch.setattr(lottery_scheduler.DltNotificationService, "notify_sync_exception",
                        fail_notification)
    barrier = Barrier(4)

    def operation(kind):
        barrier.wait(timeout=5)
        start = perf_counter()
        if kind == "http":
            response = client.post("/api/v1/fund/nav-records", json={
                "fund_code": "synthetic", "fund_name": "Synthetic",
                "nav_date": "2026-01-01", "unit_nav": "1.25",
            })
            assert response.status_code == 200, response.text
        elif kind == "fund":
            fund_scheduler._run_scheduled_fund_nav_sync()
        elif kind == "lottery":
            lottery_scheduler._run_scheduled_dlt_sync()
        else:
            # Delivery history persistence only; no external notification is sent.
            with maintenance.database_maintenance.activity() as admitted, env.sessions() as session:
                assert admitted
                session.add(NotificationDeliveryRunModel(
                    channel="test", status="sent", title="Synthetic delivery",
                ))
                session.commit()
        return perf_counter()-start

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            waits = list(executor.map(operation, ["http", "fund", "lottery", "notification"]))
        from app.plugins.fund.infrastructure.persistence.models import FundNavSyncRunModel

        for model in (FundNavRecordModel, FundNavSyncRunModel,
                      LotterySyncRunModel, NotificationDeliveryRunModel):
            assert count(env, model) == 1
        env.gate.begin_restore()
        env.gate.drain()
        assert client.post("/api/v1/fund/nav-records", json={}).status_code == 503
        fund_scheduler._run_scheduled_fund_nav_sync()
        lottery_scheduler._run_scheduled_dlt_sync()
        assert count(env, FundNavSyncRunModel) == 1
        assert count(env, LotterySyncRunModel) == 1
    finally:
        env.gate.finish("COMPLETED", usable=True)
        client.close()
    evidence("request_scheduler_overlap", env, committed=4, lock_errors=0,
             max_wait=max(waits), maintenance_blocks=True)


@pytest.mark.parametrize("foreign_keys", [False, True])
def test_foreign_key_orphan_and_check(sqlite_env, foreign_keys):
    env = sqlite_env
    with env.engine.connect() as connection:
        connection.exec_driver_sql(f"PRAGMA foreign_keys={'ON' if foreign_keys else 'OFF'}")
        connection.commit()
        with database.Session(bind=connection) as session:
            session.add(FundNavRecordModel(fund_id=999, nav_date=date(2026, 1, 1), unit_nav=1))
            if foreign_keys:
                with pytest.raises(IntegrityError):
                    session.commit()
                session.rollback()
            else:
                session.commit()
        violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        assert len(violations) == (0 if foreign_keys else 1)
        connection.commit()
        try:
            connection.exec_driver_sql(
                "INSERT INTO fund_nav_records (fund_id,nav_date,unit_nav,source,note,created_at,updated_at) "
                "VALUES (998,'2026-01-02',1,'test','','2026-01-01','2026-01-01')"
            )
            connection.commit()
            assert not foreign_keys
        except IntegrityError:
            connection.rollback()
            assert foreign_keys
        physical_count = sum(len(connection.exec_driver_sql(
            f'PRAGMA foreign_key_list("{table.name}")').fetchall())
            for table in Base.metadata.tables.values())
        assert physical_count == sum(len(t.foreign_keys) for t in Base.metadata.tables.values())
        evidence("foreign_keys", env, enabled=foreign_keys, constraint_count=physical_count,
                 affected_tables=sorted(t.name for t in Base.metadata.tables.values() if t.foreign_keys),
                 orm_orphan_accepted=not foreign_keys, raw_orphan_accepted=not foreign_keys)


def test_abrupt_exit_discards_uncommitted_write(sqlite_env):
    env = sqlite_env
    with env.sessions() as session:
        fund_write(session, "before-crash")
        session.commit()
    # Child only imports stdlib, owns only this temporary DB, and deliberately skips cleanup.
    result = subprocess.run([sys.executable, "-c", """
import os, sqlite3, sys
c = sqlite3.connect(sys.argv[1])
c.execute("UPDATE funds SET name='committed-before-crash'")
c.commit()
c.execute("UPDATE funds SET name='uncommitted'")
os._exit(23)
""", str(env.path)], timeout=10, check=False)
    assert result.returncode == 23
    sidecars = [suffix for suffix in ("-wal", "-shm", "-journal")
                if Path(str(env.path)+suffix).exists()]
    env.engine.dispose()
    with env.sessions() as session:
        assert session.scalar(select(FundModel.name)) == "committed-before-crash"
        assert session.execute(text("PRAGMA quick_check")).fetchall() == [("ok",)]
    evidence("process_exit", env, committed_preserved=True, uncommitted_rolled_back=True,
             sidecars_before_reopen=sidecars)


def test_profile_fetch_does_not_hold_writer_lock(sqlite_env):
    env = sqlite_env
    with env.sessions() as session:
        for code in ("profile-1", "profile-2"):
            fund = fund_write(session, code)
            session.add(FundPositionModel(fund=fund, shares=1, cost_price=1, total_cost=1))
        session.commit()
    fetching, release = Event(), Event()

    class SlowProfileSource:
        def fetch_profile_type(self, code):
            if code == "profile-2":
                fetching.set()
                if not release.wait(20):
                    raise RuntimeError("Synthetic profile release timed out")
            return "QDII"

    def profiles():
        with env.sessions() as session:
            return FundService(FundRepository(session), nav_source=SlowProfileSource()).sync_held_fund_profiles()

    with ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(profiles)
        try:
            assert fetching.wait(5)
            start = perf_counter()
            outcome = "committed"
            with env.sessions() as session:
                session.add(NotificationDeliveryRunModel(
                    channel="test", status="sent", title="During profile fetch",
                ))
                try:
                    session.commit()
                except OperationalError as exc:
                    assert "locked" in str(exc).lower()
                    session.rollback()
                    outcome = "locked_rolled_back"
            elapsed = perf_counter()-start
        finally:
            release.set()
        result = pending.result(timeout=10)
    evidence("profile_network_lock", env, result=outcome, wait_seconds=elapsed)
    assert result.updated == 2
    assert outcome == "committed"
    assert count(env, NotificationDeliveryRunModel) == 1
    with env.sessions() as session:
        assert session.scalars(select(FundModel.fund_type)).all() == ["QDII", "QDII"]


@pytest.mark.parametrize("failure", ["provider", "commit"])
def test_profile_batch_failure_contract(sqlite_env, monkeypatch, failure):
    env = sqlite_env
    with env.sessions() as session:
        for code in ("profile-1", "profile-2"):
            fund = fund_write(session, code)
            session.add(FundPositionModel(fund=fund, shares=1, cost_price=1, total_cost=1))
        session.commit()

    class Source:
        def fetch_profile_type(self, code):
            if failure == "provider" and code == "profile-2":
                raise RuntimeError("Synthetic provider failure")
            return "QDII"

    with env.sessions() as session:
        repository = FundRepository(session)
        calls = []
        original_commit = repository.commit

        def commit():
            calls.append("commit")
            if failure == "commit":
                raise RuntimeError("Synthetic commit failure")
            original_commit()

        monkeypatch.setattr(repository, "commit", commit)
        service = FundService(repository, nav_source=Source())
        if failure == "provider":
            result = service.sync_held_fund_profiles()
            assert (result.updated, result.failed) == (1, 1)
        else:
            with pytest.raises(RuntimeError, match="Synthetic commit failure"):
                service.sync_held_fund_profiles()
            session.rollback()
        assert calls == ["commit"]
    with env.sessions() as session:
        types = session.scalars(select(FundModel.fund_type).order_by(FundModel.code)).all()
        assert types == (["QDII", "test"] if failure == "provider" else ["test", "test"])


def load_launcher():
    path = Path(__file__).parents[1] / "scripts/check_sqlite_concurrency.py"
    spec = spec_from_file_location("sqlite_evidence_launcher", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launcher_cannot_bypass_isolation(monkeypatch, tmp_path):
    launcher = load_launcher()
    monkeypatch.chdir(tmp_path)
    sentinel = tmp_path / "pytest"
    sentinel.mkdir()
    marker = sentinel / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["check_sqlite_concurrency.py", "--child"])
    with pytest.raises(SystemExit) as exc:
        launcher.main()
    assert exc.value.code == 2
    assert marker.read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize("option", [[], ["--full"], ["--fk-experiment"]])
def test_launcher_cleans_settings_and_pytest_controls(monkeypatch, tmp_path, option):
    launcher = load_launcher()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DATABASE_URL=invalid\n", encoding="utf-8")
    for key, value in {
        "database_url": "invalid", "HaP_Admin_Password_Hash": "synthetic-invalid",
        "PYTEST_ADDOPTS": "--collect-only", "PYTEST_PLUGINS": "nonexistent",
        "PYTHONOPTIMIZE": "1",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(sys, "argv", ["check_sqlite_concurrency.py", *option])
    observed = []

    def run(command, *, cwd, env):
        normalized = {key.casefold(): value for key, value in env.items()}
        assert "hap_admin_password_hash" not in normalized
        assert "pytest_addopts" not in normalized
        assert "pytest_plugins" not in normalized
        assert "pythonoptimize" not in normalized
        assert normalized["pytest_disable_plugin_autoload"] == "1"
        assert Path(cwd).is_dir() and Path(cwd) != tmp_path
        assert not (Path(cwd) / ".env").exists()
        assert normalized["database_url"] == f"sqlite:///{Path(cwd) / 'bootstrap.db'}"
        assert command[command.index("--basetemp") + 1] == str(Path(cwd) / "pytest")
        assert ("--ignore" in command) is (option == ["--fk-experiment"])
        observed.append(cwd)
        return 0

    monkeypatch.setattr(launcher.subprocess, "call", run)
    assert launcher.main() == 0
    assert len(observed) == 1 and not Path(observed[0]).exists()
