from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, text

from app.core.database import migrations


def test_database_migrations_stamp_legacy_schema_before_upgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_engine = create_engine("sqlite://")
    with database_engine.begin() as connection:
        connection.execute(text("CREATE TABLE existing_hap_data (id INTEGER PRIMARY KEY)"))

    stamp = Mock()
    upgrade = Mock()
    monkeypatch.setattr(migrations, "engine", database_engine)
    monkeypatch.setattr(migrations, "create_database_schema", Mock())
    monkeypatch.setattr(migrations.command, "stamp", stamp)
    monkeypatch.setattr(migrations.command, "upgrade", upgrade)

    migrations.run_database_migrations()

    stamp.assert_called_once()
    assert stamp.call_args.args[1] == migrations.LEGACY_SCHEMA_REVISION
    upgrade.assert_called_once()
    assert upgrade.call_args.args[1] == "head"


def test_database_migrations_do_not_restamp_managed_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_engine = create_engine("sqlite://")
    with database_engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))

    stamp = Mock()
    upgrade = Mock()
    monkeypatch.setattr(migrations, "engine", database_engine)
    create_schema = Mock()
    calls: list[str] = []
    create_schema.side_effect = lambda: calls.append("create_schema")
    upgrade.side_effect = lambda *_args: calls.append("upgrade")
    monkeypatch.setattr(migrations, "create_database_schema", create_schema)
    monkeypatch.setattr(migrations.command, "stamp", stamp)
    monkeypatch.setattr(migrations.command, "upgrade", upgrade)

    migrations.run_database_migrations()

    stamp.assert_not_called()
    upgrade.assert_called_once()
    create_schema.assert_called_once()
    assert calls == ["upgrade", "create_schema"]


def test_fund_nav_sync_migration_skips_table_created_by_orm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260730_1930_add_fund_nav_sync_runs.py"
    )
    spec = spec_from_file_location("fund_nav_sync_revision", revision_path)
    assert spec is not None and spec.loader is not None
    revision = module_from_spec(spec)
    spec.loader.exec_module(revision)
    database_engine = create_engine("sqlite://")
    with database_engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE fund_nav_sync_runs (id INTEGER PRIMARY KEY)")
        )
        create_table = Mock()
        monkeypatch.setattr(revision.op, "get_bind", lambda: connection)
        monkeypatch.setattr(revision.op, "create_table", create_table)

        revision.upgrade()

    create_table.assert_not_called()


def test_fund_target_weight_migration_adds_missing_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260801_2300_add_fund_position_target_weight.py"
    )
    spec = spec_from_file_location("fund_target_weight_revision", revision_path)
    assert spec is not None and spec.loader is not None
    revision = module_from_spec(spec)
    spec.loader.exec_module(revision)
    database_engine = create_engine("sqlite://")
    with database_engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE fund_positions (id INTEGER PRIMARY KEY)")
        )
        add_column = Mock()
        monkeypatch.setattr(revision.op, "get_bind", lambda: connection)
        monkeypatch.setattr(revision.op, "add_column", add_column)

        revision.upgrade()

    add_column.assert_called_once()
    assert add_column.call_args.args[0] == "fund_positions"
    assert add_column.call_args.args[1].name == "target_weight"
