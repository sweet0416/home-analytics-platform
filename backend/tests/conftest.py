from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database.base import Base
from app.core.database.session import get_db
from app.main import create_app
from app.core.backup import models as backup_models  # noqa: F401
from app.plugins.lottery.infrastructure.persistence import models  # noqa: F401
from app.plugins.lottery.infrastructure.persistence.repositories import LotteryRepository

TEST_DB_PATH = Path("data/test/hap_test.db")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()
    LotteryRepository(db_session).ensure_dlt_seed_data()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
