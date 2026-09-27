from pathlib import Path

from sqlalchemy import Engine, inspect

from alembic import command
from alembic.config import Config
from app.core.database.maintenance import require_recovered_database
from app.core.database.session import create_database_schema, engine

LEGACY_SCHEMA_REVISION = "20260729_2130"


def migration_config() -> Config:
    project_root = Path(__file__).resolve().parents[3]
    config = Config(project_root / "alembic.ini")
    config.set_main_option("script_location", str(project_root / "alembic"))
    return config


def run_database_migrations(*, target_engine: Engine | None = None) -> None:
    """Bring legacy create_all databases under Alembic, then upgrade them."""
    selected = target_engine if target_engine is not None else engine
    if target_engine is None and selected.url.get_backend_name() == "sqlite" and selected.url.database:
        require_recovered_database(Path(selected.url.database))
    config = migration_config()
    config.attributes["configure_logger"] = target_engine is None
    managed = inspect(selected).has_table("alembic_version")
    if not managed:
        create_database_schema() if target_engine is None else create_database_schema(selected)
    with selected.begin() as connection:
        config.attributes["connection"] = connection
        if not managed:
            command.stamp(config, LEGACY_SCHEMA_REVISION)
        command.upgrade(config, "head")
    if managed:
        create_database_schema() if target_engine is None else create_database_schema(selected)


if __name__ == "__main__":
    run_database_migrations()
