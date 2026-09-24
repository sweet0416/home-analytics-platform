from collections.abc import Generator
from hashlib import pbkdf2_hmac
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.auth import COOKIE_NAME, create_session
from app.core.backup import models as backup_models  # noqa: F401
from app.core.config.settings import get_settings
from app.core.database.base import Base
from app.core.database.session import get_db
from app.main import create_app
from app.plugins.fund.infrastructure.persistence import models as fund_models  # noqa: F401
from app.plugins.lottery.infrastructure.persistence import models  # noqa: F401
from app.plugins.lottery.infrastructure.persistence.repositories import LotteryRepository

_TEST_SALT = bytes(16)
_TEST_DIGEST = pbkdf2_hmac("sha256", b"test-admin-password", _TEST_SALT, 600_000)
_TEST_PASSWORD_HASH = f"pbkdf2_sha256$600000${_TEST_SALT.hex()}${_TEST_DIGEST.hex()}"

@pytest.fixture()
def db_session(tmp_path: Path) -> Generator[Session, None, None]:
    test_db_path = tmp_path / "hap_test.db"
    test_database_url = f"sqlite:///{test_db_path}"
    engine = create_engine(test_database_url, connect_args={"check_same_thread": False})
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
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("HAP_ADMIN_PASSWORD_HASH", _TEST_PASSWORD_HASH)
    get_settings.cache_clear()
    app = create_app()
    LotteryRepository(db_session).ensure_dlt_seed_data()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        session_id, csrf = create_session("testclient")
        test_client.cookies.set(COOKIE_NAME, session_id)
        test_client.headers["X-CSRF-Token"] = csrf
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()
