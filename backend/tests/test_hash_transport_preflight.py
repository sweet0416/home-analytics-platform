"""Synthetic checks for preflight isolation and optimized Python execution."""

import base64
import json
import os
import subprocess
import sys
from hashlib import pbkdf2_hmac
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import check_hash_transport as preflight


@pytest.fixture(scope="module")
def synthetic_hash() -> str:
    salt = bytes.fromhex("ab" * 16)
    digest = pbkdf2_hmac("sha256", preflight.PASSWORD.encode(), salt, 600_000).hex()
    return f"pbkdf2_sha256$600000${salt.hex()}${digest}"


def _compose_result(encoded: str) -> subprocess.CompletedProcess[str]:
    payload = {
        "services": {"hash-probe": {"environment": {"HAP_ADMIN_PASSWORD_HASH_B64": encoded}}}
    }
    return subprocess.CompletedProcess([], 0, json.dumps(payload), "")


def _mock_compose(monkeypatch: pytest.MonkeyPatch, encoded: str) -> None:
    monkeypatch.setattr(preflight.shutil, "which", lambda _: "docker-compose")

    def run(command: list[str], **options: object) -> subprocess.CompletedProcess[str]:
        env = options["env"]
        if not isinstance(env, dict) or env.get("HAP_ADMIN_PASSWORD_HASH_B64") != encoded:
            raise RuntimeError("MOCK_SYNTHETIC_VALUE_MISSING")
        if any(
            key.casefold() in {"hap_admin_password_hash", "backend_workers", "cors_origins"}
            for key in env
        ):
            raise RuntimeError("MOCK_EXTERNAL_CONFIG_LEAKED")
        if (
            "--env-file" not in command
            or Path(command[command.index("--env-file") + 1]).read_text(encoding="utf-8") != ""
        ):
            raise RuntimeError("MOCK_DOTENV_NOT_ISOLATED")
        if Path(options["cwd"]) == Path.cwd():
            raise RuntimeError("MOCK_COMPOSE_CWD_NOT_ISOLATED")
        return _compose_result(encoded)

    monkeypatch.setattr(preflight.subprocess, "run", run)


@pytest.mark.parametrize(
    "scenario",
    ["clean", "raw_env", "b64_env", "dotenv", "unrelated", "mixed_case"],
)
def test_preflight_ignores_external_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, synthetic_hash: str, scenario: str
) -> None:
    encoded = base64.b64encode(synthetic_hash.encode()).decode("ascii")
    external = {
        "raw_env": {"HAP_ADMIN_PASSWORD_HASH": synthetic_hash},
        "b64_env": {"HAP_ADMIN_PASSWORD_HASH_B64": encoded},
        "unrelated": {"BACKEND_WORKERS": "999", "CORS_ORIGINS": "not-json"},
        "mixed_case": {"hap_admin_password_hash": synthetic_hash, "Backend_Workers": "999"},
    }.get(scenario, {})
    monkeypatch.chdir(tmp_path)
    if scenario == "dotenv":
        (tmp_path / ".env").write_text(
            "HAP_ADMIN_PASSWORD_HASH=" + synthetic_hash + "\nBACKEND_WORKERS=999\n",
            encoding="utf-8",
        )
    _mock_compose(monkeypatch, encoded)
    with patch.dict(os.environ, external, clear=True):
        preflight.check(synthetic_hash)


@pytest.mark.parametrize(
    ("fault", "expected"),
    [
        ("invalid_format", "INVALID_SYNTHETIC_HASH"),
        ("correct_rejected", "CORRECT_PASSWORD_REJECTED"),
        ("wrong_accepted", "WRONG_PASSWORD_ACCEPTED"),
        ("content_changed", "COMPOSE_VALUE_CHANGED"),
        ("format_broken", "COMPOSE_OUTPUT_INVALID"),
    ],
)
def test_preflight_detects_injected_faults(
    monkeypatch: pytest.MonkeyPatch, synthetic_hash: str, fault: str, expected: str
) -> None:
    monkeypatch.setattr(preflight.shutil, "which", lambda _: "docker")
    if fault == "correct_rejected":
        monkeypatch.setattr(preflight, "verify_password", lambda *_: False)
    elif fault == "wrong_accepted":
        monkeypatch.setattr(preflight, "verify_password", lambda *_: True)
    elif fault in {"content_changed", "format_broken"}:
        altered = synthetic_hash[:-1] + ("0" if synthetic_hash[-1] != "0" else "1")
        encoded = base64.b64encode(altered.encode()).decode("ascii")
        if fault == "format_broken":
            encoded = "not-base64"
        monkeypatch.setattr(preflight.subprocess, "run", lambda *_, **__: _compose_result(encoded))
    supplied = "invalid" if fault == "invalid_format" else synthetic_hash
    with pytest.raises(RuntimeError) as captured:
        preflight.check(supplied)
    if str(captured.value) != expected:
        pytest.fail("Unexpected failure classification", pytrace=False)


def test_main_does_not_print_pass_after_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def reject(_: str) -> None:
        raise RuntimeError("CORRECT_PASSWORD_REJECTED")

    monkeypatch.setattr(preflight, "check", reject)
    with pytest.raises(RuntimeError, match="CORRECT_PASSWORD_REJECTED"):
        preflight.main()
    if "PASS" in capsys.readouterr().out:
        pytest.fail("Preflight printed PASS after failure", pytrace=False)


MODE_CHECK = """
import base64, json, subprocess
from hashlib import pbkdf2_hmac
from scripts import check_hash_transport as p
salt = bytes.fromhex('ab' * 16)
digest = pbkdf2_hmac('sha256', p.PASSWORD.encode(), salt, 600000).hex()
h = f'pbkdf2_sha256$600000${salt.hex()}${digest}'
p.shutil.which = lambda _: 'docker'
def compose(*args, **kwargs):
    value = kwargs['env']['HAP_ADMIN_PASSWORD_HASH_B64']
    return subprocess.CompletedProcess([], 0, json.dumps({'services': {'hash-probe': {'environment': {'HAP_ADMIN_PASSWORD_HASH_B64': value}}}}), '')
p.subprocess.run = compose
def expect(code, action):
    try:
        action()
    except RuntimeError as error:
        if str(error) != code:
            raise SystemExit(2)
    else:
        raise SystemExit(3)
p.check(h)
expect('INVALID_SYNTHETIC_HASH', lambda: p.check('invalid'))
original = p.verify_password
p.verify_password = lambda *_: False
expect('CORRECT_PASSWORD_REJECTED', lambda: p.check(h))
p.verify_password = lambda *_: True
expect('WRONG_PASSWORD_ACCEPTED', lambda: p.check(h))
p.verify_password = original
def changed(*args, **kwargs):
    altered = h[:-1] + ('0' if h[-1] != '0' else '1')
    value = base64.b64encode(altered.encode()).decode()
    return subprocess.CompletedProcess([], 0, json.dumps({'services': {'hash-probe': {'environment': {'HAP_ADMIN_PASSWORD_HASH_B64': value}}}}), '')
p.subprocess.run = changed
expect('COMPOSE_VALUE_CHANGED', lambda: p.check(h))
print('MODE_PASS')
"""


@pytest.mark.parametrize("mode", ["normal", "python_o", "pythonoptimize"])
def test_preflight_checks_survive_python_optimization(mode: str, tmp_path: Path) -> None:
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"}
    }
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    command = [sys.executable]
    if mode == "python_o":
        command.append("-O")
    if mode == "pythonoptimize":
        env["PYTHONOPTIMIZE"] = "1"
    result = subprocess.run(
        [*command, "-c", MODE_CHECK],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    if result.returncode != 0 or result.stdout.strip() != "MODE_PASS":
        pytest.fail("Optimized-mode preflight regression failed", pytrace=False)
