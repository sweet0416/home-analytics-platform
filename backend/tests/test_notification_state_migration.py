from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.core.database.migrations import migration_config, run_database_migrations


def test_legacy_history_survives_managed_upgrade(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    try:
        with engine.begin() as connection:
            connection.execute(text("""
                CREATE TABLE notification_delivery_runs (
                    id INTEGER PRIMARY KEY, source VARCHAR(64), channel VARCHAR(32),
                    status VARCHAR(32), title VARCHAR(160), message_preview TEXT,
                    result_message TEXT, provider_message_id VARCHAR(255),
                    sent_at DATETIME, created_at DATETIME
                )
            """))
            connection.execute(text("""
                INSERT INTO notification_delivery_runs
                    (id, source, channel, status, title, message_preview, result_message)
                VALUES (1, 'infrastructure_health', 'bark', 'sent', 'legacy', 'legacy prose', 'sent')
            """))
            config = migration_config()
            config.attributes.update(connection=connection, configure_logger=False)
            command.stamp(config, "20260808_0022")
        run_database_migrations(target_engine=engine)
        run_database_migrations(target_engine=engine)  # Restart remains idempotent.
        with engine.connect() as connection:
            row = connection.execute(text(
                "SELECT message_preview, result_message, health_state FROM notification_delivery_runs WHERE id=1"
            )).one()
            assert row == ("legacy prose", "sent", None)
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260927_1200"
    finally:
        engine.dispose()


def test_fresh_database_orm_and_migration_are_compatible(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    try:
        run_database_migrations(target_engine=engine)
        column = next(c for c in inspect(engine).get_columns("notification_delivery_runs") if c["name"] == "health_state")
        assert column["nullable"] is True
        run_database_migrations(target_engine=engine)
    finally:
        engine.dispose()
