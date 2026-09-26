"""Synthetic, secret-safe preflight for the isolated Base64 Compose transport.

Run from repository root with the backend virtualenv's Python. Never pass a real
administrator hash to this script: it generates disposable values in memory.
"""

import base64
import json
import os
import secrets
import shutil
import subprocess
import tempfile
from binascii import Error as Base64Error
from hashlib import pbkdf2_hmac
from pathlib import Path
from unittest.mock import patch

from app.core.auth import valid_password_hash, verify_password
from app.core.config.settings import Settings

COMPOSE = Path(__file__).resolve().parents[2] / "deploy/hash-transport-test/docker-compose.yml"
PASSWORD = "synthetic-hash-transport-test-only"


def check(password_hash: str) -> None:
    if not valid_password_hash(password_hash):
        raise RuntimeError("INVALID_SYNTHETIC_HASH")
    encoded = base64.b64encode(password_hash.encode()).decode("ascii")
    # Settings normally reads both the caller's environment and .env.
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings(_env_file=None, hap_admin_password_hash_b64=encoded)
    actual_hash = settings.admin_password_hash()
    if actual_hash != password_hash:
        raise RuntimeError("APPLICATION_VALUE_CHANGED")
    if not verify_password(PASSWORD, actual_hash):
        raise RuntimeError("CORRECT_PASSWORD_REJECTED")
    if verify_password("wrong", actual_hash):
        raise RuntimeError("WRONG_PASSWORD_ACCEPTED")

    compose = shutil.which("docker-compose")
    docker = shutil.which("docker") if compose is None else None
    if compose is None and docker is None:
        raise RuntimeError("DOCKER_COMPOSE_UNAVAILABLE")
    with tempfile.TemporaryDirectory(prefix="hap-hash-preflight-") as temporary:
        empty_env = Path(temporary) / "empty.env"
        empty_env.write_text("", encoding="utf-8")
        env = {
            key.upper(): value
            for key, value in os.environ.items()
            if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"}
        }
        env.update(
            HOME=temporary,
            USERPROFILE=temporary,
            DOCKER_CONFIG=temporary,
            HAP_ADMIN_PASSWORD_HASH_B64=encoded,
            HAP_TEST_PASSWORD_B64=base64.b64encode(PASSWORD.encode()).decode("ascii"),
        )
        try:
            result = subprocess.run(
                [
                    *([compose] if compose is not None else [docker, "compose"]),
                    "--env-file",
                    str(empty_env),
                    "-f",
                    str(COMPOSE),
                    "config",
                    "--format",
                    "json",
                ],
                env=env,
                cwd=temporary,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise RuntimeError("COMPOSE_EXECUTION_FAILED") from None
    # Compose output may contain the synthetic hash. Never print stdout/stderr.
    if result.returncode:
        raise RuntimeError("COMPOSE_CONFIG_FAILED")
    try:
        actual = json.loads(result.stdout)["services"]["hash-probe"]["environment"][
            "HAP_ADMIN_PASSWORD_HASH_B64"
        ]
        decoded = base64.b64decode(actual, validate=True).decode("utf-8")
    except (Base64Error, KeyError, TypeError, ValueError):
        raise RuntimeError("COMPOSE_OUTPUT_INVALID") from None
    if actual != encoded or decoded != password_hash:
        raise RuntimeError("COMPOSE_VALUE_CHANGED")


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
