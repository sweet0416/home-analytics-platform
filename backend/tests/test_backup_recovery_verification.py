import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database.migrations import run_database_migrations
from app.plugins.fund.infrastructure.persistence.models import FundModel, FundNavRecordModel

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture()
def backup(tmp_path: Path) -> Path:
    database = tmp_path / "source.db"
    engine = create_engine(f"sqlite:///{database}")
    try:
        run_database_migrations(target_engine=engine)
        with Session(engine) as session:
            fund = FundModel(code="SYNTH001", name="Synthetic fund")
            session.add(fund)
            session.flush()
            session.add(FundNavRecordModel(fund_id=fund.id, nav_date=date(2026, 1, 1), unit_nav=Decimal("1.0000")))
            session.commit()
    finally:
        engine.dispose()
    target = tmp_path / "hap_test_backup.db"
    with sqlite3.connect(database) as source, sqlite3.connect(target) as destination:
        source.backup(destination)
    return target


def run_verifier(source: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    env["DATABASE_URL"] = "sqlite:///DO_NOT_CREATE.db"
    env["BACKUP_RETENTION_COUNT"] = "invalid"
    env["HAP_ADMIN_PASSWORD_HASH"] = "synthetic-invalid"
    (tmp_path / ".env").write_text("BACKUP_RETENTION_COUNT=invalid\n", encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "scripts.verify_backup", str(source)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )


def test_current_backup_recovers_without_changing_source(backup: Path, tmp_path: Path) -> None:
    original = hashlib.sha256(backup.read_bytes()).hexdigest()
    result = run_verifier(backup, tmp_path)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["source_sha256"] == report["copy_sha256"] == original
    assert report["alembic_revision"] == report["alembic_after"]
    assert report["quick_check"] == report["integrity_check"] == "ok"
    assert report["counts"]["funds"] == report["counts"]["fund_nav_records"] == 1
    assert report["app_read"] == report["health_probe"] == "ok"
    assert report["recovery_status"] == "RECOVERY_VERIFIED"
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == original
    assert not (tmp_path / "DO_NOT_CREATE.db").exists()
    assert list(tmp_path.glob("hap-recovery-*")) == []


def test_old_backup_migrates_only_on_disposable_copy(backup: Path, tmp_path: Path) -> None:
    with sqlite3.connect(backup) as connection:
        connection.execute("DROP INDEX ix_fund_transactions_external_trade")
        for column in (
            "external_source", "external_trade_id", "external_trade_type",
            "external_business_code", "external_status", "external_confirm_status",
            "confirm_date", "source_updated_at",
        ):
            connection.execute(f"ALTER TABLE fund_transactions DROP COLUMN {column}")
        connection.execute("UPDATE alembic_version SET version_num='20260808_0021'")
    original = hashlib.sha256(backup.read_bytes()).hexdigest()
    result = run_verifier(backup, tmp_path)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["alembic_revision"] == "20260808_0021"
    assert report["alembic_after"] != report["alembic_revision"]
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == original


@pytest.mark.parametrize("kind", ["zero", "random", "truncated", "missing_schema", "bad_revision", "corrupt"])
def test_invalid_backup_is_rejected(backup: Path, tmp_path: Path, kind: str) -> None:
    candidate = tmp_path / f"hap_{kind}.db"
    if kind == "zero":
        candidate.touch()
    elif kind == "random":
        candidate.write_bytes(b"not a SQLite database")
    elif kind == "truncated":
        candidate.write_bytes(backup.read_bytes()[:64])
    elif kind == "missing_schema":
        with sqlite3.connect(candidate) as connection:
            connection.execute("CREATE TABLE other (id INTEGER)")
    elif kind == "bad_revision":
        shutil.copyfile(backup, candidate)
        with sqlite3.connect(candidate) as connection:
            connection.execute("UPDATE alembic_version SET version_num='unknown_revision'")
    else:
        candidate.write_bytes(backup.read_bytes()[:100] + b"broken" * 20)
    original = candidate.read_bytes()
    result = run_verifier(candidate, tmp_path)
    assert result.returncode == 1
    assert "RECOVERY_UNVERIFIED" in result.stderr
    assert candidate.read_bytes() == original
