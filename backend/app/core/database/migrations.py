from pathlib import Path

from sqlalchemy import inspect

from alembic import command
from alembic.config import Config
from app.core.database.session import create_database_schema, engine

LEGACY_SCHEMA_REVISION = "20260729_2130"


def run_database_migrations() -> None:
    """Bring legacy create_all databases under Alembic, then upgrade them."""
    create_database_schema()

    project_root = Path(__file__).resolve().parents[3]
    config = Config(project_root / "alembic.ini")

    if not inspect(engine).has_table("alembic_version"):
        command.stamp(config, LEGACY_SCHEMA_REVISION)

    command.upgrade(config, "head")


if __name__ == "__main__":
    run_database_migrations()
