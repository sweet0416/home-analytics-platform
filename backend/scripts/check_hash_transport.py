"""Synthetic, secret-safe preflight for the isolated Base64 Compose transport.

Run from repository root with the backend virtualenv's Python. Never pass a real
administrator hash to this script: it generates disposable values in memory.
"""

import base64
import json
import os
import secrets
import subprocess
from hashlib import pbkdf2_hmac
from pathlib import Path

from app.core.auth import valid_password_hash, verify_password
from app.core.config.settings import Settings

COMPOSE = Path(__file__).resolve().parents[2] / "deploy/hash-transport-test/docker-compose.yml"
PASSWORD = "synthetic-hash-transport-test-only"


def check(password_hash: str) -> None:
    assert valid_password_hash(password_hash)
    encoded = base64.b64encode(password_hash.encode()).decode("ascii")
    settings = Settings(hap_admin_password_hash_b64=encoded)
    assert settings.admin_password_hash() == password_hash
    assert verify_password(PASSWORD, settings.admin_password_hash())
    assert not verify_password("wrong", settings.admin_password_hash())

    env = os.environ.copy()
    env.pop("HAP_ADMIN_PASSWORD_HASH", None)
    env["HAP_ADMIN_PASSWORD_HASH_B64"] = encoded
    env["HAP_TEST_PASSWORD_B64"] = base64.b64encode(PASSWORD.encode()).decode("ascii")
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "config", "--format", "json"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    # Compose output may contain the synthetic hash. Never print stdout/stderr.
    if result.returncode:
        raise RuntimeError("Local Compose preflight failed (details intentionally suppressed)")
    actual = json.loads(result.stdout)["services"]["hash-probe"]["environment"][
        "HAP_ADMIN_PASSWORD_HASH_B64"
    ]
    assert actual == encoded, "Compose changed the encoded value"
    assert base64.b64decode(actual, validate=True).decode() == password_hash


def main() -> None:
    groups: set[tuple[str, str]] = set()
    count = 0
    # Bounded search: four prefix combinations generally appear quickly.
    for index in range(64):
        salt = bytes([0xA0 if index % 2 else 0x10]) + secrets.token_bytes(15)
        digest = pbkdf2_hmac("sha256", PASSWORD.encode(), salt, 600_000).hex()
        category = (
            "letter" if salt.hex()[0].isalpha() else "digit",
            "letter" if digest[0].isalpha() else "digit",
        )
        if category in groups and index >= 8:
            continue
        password_hash = f"pbkdf2_sha256$600000${salt.hex()}${digest}"
        check(password_hash)
        groups.add(category)
        count += 1
        if len(groups) == 4 and index >= 8:
            break
    if len(groups) != 4:
        raise RuntimeError("Synthetic prefix coverage incomplete")
    print(
        f"PASS: {count} synthetic valid hashes, four salt/digest prefix groups; full-value Compose equality"
    )


if __name__ == "__main__":
    main()
