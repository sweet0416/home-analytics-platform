from base64 import b64encode
from hashlib import pbkdf2_hmac
from secrets import token_bytes

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.core.auth import COOKIE_NAME
from app.core.config.settings import Settings, get_settings
from app.main import create_app


def test_api_requires_login_and_machine_token(client: TestClient) -> None:
    client.cookies.clear()
    for method, path in (
        ("get", "/api/v1/system/backups"),
        ("get", "/api/v1/system/backups/sample.db/download"),
        ("post", "/api/v1/system/backups/sample.db/restore"),
        ("post", "/api/v1/system/notifications/test"),
        ("post", "/api/v1/fund/reports/daily/ai-summary"),
        ("get", "/api/v1/fund/positions"),
        ("post", "/api/v1/fund/positions"),
        ("delete", "/api/v1/fund/positions/1"),
        ("get", "/api/v1/fund/transactions"),
    ):
        assert client.request(method, path).status_code == 401
    assert client.get("/api/v1/system/health").status_code == 200
    assert client.post("/api/v1/fund/integrations/ttskill/base-infos", json={}).status_code in (
        401,
        503,
    )


def test_login_csrf_and_logout_invalidate_session(client: TestClient) -> None:
    client.cookies.clear()
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "wrong"}
        ).status_code
        == 401
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "test-admin-password"},
    )
    assert response.status_code == 200
    assert "test-admin-password" not in response.text
    assert get_settings().hap_admin_password_hash not in response.text
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    old_cookie = client.cookies.get(COOKIE_NAME)
    assert old_cookie
    assert client.get("/api/v1/auth/me").status_code == 200
    assert client.get("/api/v1/fund/positions").status_code == 200
    csrf = response.json()["data"]["csrf_token"]
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
    client.cookies.set(COOKIE_NAME, old_cookie)
    assert client.get("/api/v1/system/backups").status_code == 401


def test_new_routes_are_protected_by_default(client: TestClient) -> None:
    client.cookies.clear()
    assert client.get("/api/v1/unknown-future-route").status_code == 401
    assert client.get("/openapi.json").status_code == 401


def test_session_expiry_and_invalid_cookie(client: TestClient, monkeypatch) -> None:
    client.cookies.set(COOKIE_NAME, "invalid-session")
    assert client.get("/api/v1/fund/positions").status_code == 401
    session_id, _ = auth.create_session("testclient")
    client.cookies.set(COOKIE_NAME, session_id)
    assert client.get("/api/v1/fund/positions").status_code == 200
    monkeypatch.setattr(auth, "time", lambda: float("inf"))
    assert client.get("/api/v1/fund/positions").status_code == 401


def test_cross_origin_writes_and_login_are_rejected(client: TestClient) -> None:
    assert (
        client.post(
            "/api/v1/system/backups",
            headers={"Origin": "https://other.example"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "test-admin-password"},
            headers={"Origin": "https://other.example"},
        ).status_code
        == 403
    )


def test_same_origin_login_behind_proxy_with_non_default_port(client: TestClient) -> None:
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "test-admin-password"},
        headers={
            "Host": "192.168.100.249:8088",
            "Origin": "http://192.168.100.249:8088",
            "X-Forwarded-Proto": "http",
        },
    )
    assert response.status_code == 200


def test_invalid_login_payload_does_not_echo_password(client: TestClient) -> None:
    secret_input = "sensitive-password" * 100
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": secret_input},
    )
    assert response.status_code == 422
    assert secret_input not in response.text


def test_secure_cookie_when_https_is_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HAP_COOKIE_SECURE", "true")
    get_settings.cache_clear()
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "test-admin-password"},
    )
    assert response.status_code == 200
    assert "Secure" in response.headers["set-cookie"]


def test_missing_admin_hash_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="HAP_ADMIN_PASSWORD_HASH"):
        Settings(hap_admin_password_hash="").validate_auth()


def test_plaintext_or_malformed_admin_hash_is_rejected() -> None:
    for invalid_value in ("example-password", "pbkdf2_sha256$600000$bad$not-a-hash"):
        with pytest.raises(RuntimeError, match="HAP_ADMIN_PASSWORD_HASH"):
            Settings(hap_admin_password_hash=invalid_value).validate_auth()


@pytest.mark.parametrize("salt_first", ["0", "a", "b", "c", "d", "e", "f"])
def test_encoded_hash_preserves_full_value_and_authenticates(salt_first: str) -> None:
    password = "synthetic-admin-password"
    salt = bytes.fromhex(salt_first + "1" + "23" * 15)
    digest = pbkdf2_hmac("sha256", password.encode(), salt, 600_000).hex()
    password_hash = f"pbkdf2_sha256$600000${salt.hex()}${digest}"
    encoded = b64encode(password_hash.encode()).decode()
    settings = Settings(hap_admin_password_hash_b64=encoded)
    settings.validate_auth()
    assert settings.admin_password_hash() == password_hash
    assert auth.verify_password(password, settings.admin_password_hash())
    assert not auth.verify_password("incorrect", settings.admin_password_hash())


@pytest.mark.parametrize("bad", ["", "not-base64", "AA== ", "AAAA", "\ufeffAAAA"])
def test_invalid_encoded_hash_fails_closed(bad: str) -> None:
    with pytest.raises(RuntimeError, match="HAP_ADMIN_PASSWORD_HASH"):
        Settings(hap_admin_password_hash_b64=bad).validate_auth()


def test_raw_and_encoded_hash_conflict_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="HAP_ADMIN_PASSWORD_HASH"):
        Settings(
            hap_admin_password_hash="legacy", hap_admin_password_hash_b64="AAAA"
        ).validate_auth()


def test_encoded_hash_content_mutation_is_not_accepted() -> None:
    password = "synthetic-admin-password"
    salt = bytes.fromhex("ab" * 16)
    digest = pbkdf2_hmac("sha256", password.encode(), salt, 600_000).hex()
    password_hash = f"pbkdf2_sha256$600000${salt.hex()}${digest}"
    mutated = password_hash[:-1] + ("0" if password_hash[-1] != "0" else "1")
    settings = Settings(hap_admin_password_hash_b64=b64encode(mutated.encode()).decode())
    settings.validate_auth()
    assert settings.admin_password_hash() != password_hash
    assert not auth.verify_password(password, settings.admin_password_hash())


def test_unscreened_random_valid_hashes_round_trip() -> None:
    password = "synthetic-admin-password"
    for _ in range(8):
        salt = token_bytes(16)
        digest = pbkdf2_hmac("sha256", password.encode(), salt, 600_000).hex()
        password_hash = f"pbkdf2_sha256$600000${salt.hex()}${digest}"
        settings = Settings(hap_admin_password_hash_b64=b64encode(password_hash.encode()).decode())
        assert settings.admin_password_hash() == password_hash
        assert auth.verify_password(password, settings.admin_password_hash())
        assert not auth.verify_password("incorrect", settings.admin_password_hash())


@pytest.mark.parametrize("suffix", ["\n", " ", "\r\n", "$"])
def test_encoded_hash_rejects_boundary_or_extra_delimiter(suffix: str) -> None:
    salt = bytes.fromhex("ab" * 16)
    digest = pbkdf2_hmac("sha256", b"synthetic", salt, 600_000).hex()
    password_hash = f"pbkdf2_sha256$600000${salt.hex()}${digest}{suffix}"
    with pytest.raises(RuntimeError, match="HAP_ADMIN_PASSWORD_HASH"):
        Settings(
            hap_admin_password_hash_b64=b64encode(password_hash.encode()).decode()
        ).validate_auth()


def test_encoded_hash_login_and_protected_route(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    password = "synthetic-admin-password"
    salt = bytes.fromhex("af" * 16)
    digest = pbkdf2_hmac("sha256", password.encode(), salt, 600_000).hex()
    password_hash = f"pbkdf2_sha256$600000${salt.hex()}${digest}"
    monkeypatch.delenv("HAP_ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.setenv("HAP_ADMIN_PASSWORD_HASH_B64", b64encode(password_hash.encode()).decode())
    get_settings.cache_clear()
    client.cookies.clear()
    assert client.get("/api/v1/system/health").status_code == 200
    assert client.get("/api/v1/fund/positions").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": password}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/fund/positions").status_code == 200
    get_settings.cache_clear()


@pytest.mark.parametrize("password_hash", ["", "plaintext"])
def test_startup_rejects_invalid_admin_hash(
    monkeypatch: pytest.MonkeyPatch, password_hash: str
) -> None:
    monkeypatch.setenv("HAP_ADMIN_PASSWORD_HASH", password_hash)
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="HAP_ADMIN_PASSWORD_HASH"):
            with TestClient(create_app()):
                pass
    finally:
        get_settings.cache_clear()
