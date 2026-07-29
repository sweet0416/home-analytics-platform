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
    monkeypatch.setattr(migrations, "create_database_schema", Mock())
    monkeypatch.setattr(migrations.command, "stamp", stamp)
    monkeypatch.setattr(migrations.command, "upgrade", upgrade)

    migrations.run_database_migrations()

    stamp.assert_not_called()
    upgrade.assert_called_once()
