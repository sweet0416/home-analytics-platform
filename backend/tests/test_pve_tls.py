"""PVE TLS tests use ephemeral certificates and a loopback-only HTTPS server."""

import ipaddress
import json
import ssl
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

import pytest
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from urllib3.exceptions import InsecureRequestWarning

from app.core.config.settings import Settings
from app.plugins.pve.application.service import PveService
from app.plugins.pve.infrastructure.proxmox_api import ProxmoxApiClient, ProxmoxApiError


class SyntheticSettings(Settings):
    @classmethod
    def settings_customise_sources(cls, settings_cls: type[Settings], **sources: Any) -> tuple[Any, ...]:
        return (sources["init_settings"],)


def settings(**overrides: Any) -> Settings:
    return SyntheticSettings(
        **{
            "pve_enabled": True,
            "pve_url": "https://127.0.0.1",
            "pve_api_token_id": "synthetic@pve!test",
            "pve_api_token_secret": "synthetic-test-token",
            **overrides,
        }
    )


@pytest.fixture(scope="module")
def certificates(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    directory = tmp_path_factory.mktemp("synthetic-pve-tls")
    now = datetime.now(UTC)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic HAP test CA")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=2))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(True, False, False, False, False, True, True, None, None), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    paths = {name: directory / f"{name}.pem" for name in ("ca", "key", "matching", "mismatch")}
    paths["ca"].write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    paths["key"].write_bytes(server_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ))
    for name, san in (
        ("matching", x509.IPAddress(ipaddress.ip_address("127.0.0.1"))),
        ("mismatch", x509.DNSName("different.example.test")),
    ):
        cert = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic PVE")]))
            .issuer_name(ca.subject)
            .public_key(server_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=2))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([san]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
            .sign(ca_key, hashes.SHA256())
        )
        paths[name].write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return paths


@pytest.fixture
def https_server(certificates: dict[str, Path]):
    running: list[tuple[ThreadingHTTPServer, Thread]] = []

    def start(certificate: str = "matching") -> tuple[str, list[str]]:
        calls: list[str] = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                calls.append(self.path)
                data = {"version": "synthetic"} if self.path.endswith("/version") else []
                body = json.dumps({"data": data}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args: Any) -> None:
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certificates[certificate], certificates["key"])
        server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = Thread(target=lambda: server.serve_forever(poll_interval=0.05), daemon=True)
        thread.start()
        running.append((server, thread))
        return f"https://127.0.0.1:{server.server_port}", calls

    yield start
    for server, thread in running:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.mark.parametrize("verify", [False, True])
def test_bool_verification_is_preserved(verify: bool) -> None:
    from unittest.mock import Mock

    session = Mock(spec=requests.Session)
    session.headers = {}
    session.get.return_value.json.side_effect = [{"data": {}}, {"data": []}]
    client = ProxmoxApiClient(settings(pve_verify_ssl=verify), session=session)
    client.get_version()
    client.get_nodes()
    for call in session.get.call_args_list:
        assert call.kwargs["verify"] is verify
        assert call.kwargs["allow_redirects"] is False


def test_bundle_path_is_passed_to_both_request_shapes(certificates: dict[str, Path]) -> None:
    from unittest.mock import Mock

    session = Mock(spec=requests.Session)
    session.headers = {}
    session.get.return_value.json.side_effect = [{"data": {}}, {"data": []}]
    path = str(certificates["ca"])
    client = ProxmoxApiClient(settings(pve_ca_bundle=path), session=session)
    client.get_version()
    client.get_nodes()
    assert all(call.kwargs["verify"] == path for call in session.get.call_args_list)


@pytest.mark.parametrize("kind", ["missing", "directory", "empty", "garbage"])
def test_invalid_bundle_fails_before_network(kind: str, tmp_path: Path) -> None:
    from unittest.mock import Mock

    path = tmp_path / "ca.pem"
    if kind == "directory":
        path.mkdir()
    elif kind in {"empty", "garbage"}:
        path.write_text("" if kind == "empty" else "not a certificate")
    session = Mock(spec=requests.Session)
    session.headers = {}
    client = ProxmoxApiClient(settings(pve_ca_bundle=str(path)), session=session)
    with pytest.raises(ProxmoxApiError, match="PVE_CA_BUNDLE must be a readable PEM CA bundle"):
        client.get_version()
    session.get.assert_not_called()


def test_unreadable_bundle_fails_closed(certificates: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    def unreadable(**kwargs: Any) -> None:
        raise PermissionError("sensitive local path")

    monkeypatch.setattr("app.core.config.settings.ssl.create_default_context", unreadable)
    with pytest.raises(ValueError, match="PVE_CA_BUNDLE must be a readable PEM CA bundle") as error:
        settings(pve_ca_bundle=str(certificates["ca"])).pve_tls_verify()
    assert "sensitive local path" not in str(error.value)


def test_disabled_verification_ignores_bundle_and_keeps_warning(https_server) -> None:
    url, calls = https_server("mismatch")
    with requests.Session() as session:
        session.trust_env = False
        client = ProxmoxApiClient(settings(pve_url=url, pve_verify_ssl=False, pve_ca_bundle="missing.pem"), session)
        with pytest.warns(InsecureRequestWarning):
            assert client.get_version() == {"version": "synthetic"}
    assert calls == ["/api2/json/version"]


@pytest.mark.parametrize("certificate,trust_ca", [("matching", False), ("mismatch", True)])
def test_tls_rejects_untrusted_ca_and_wrong_identity(https_server, certificates: dict[str, Path], certificate: str, trust_ca: bool) -> None:
    url, calls = https_server(certificate)
    config = settings(pve_url=url, pve_ca_bundle=str(certificates["ca"]) if trust_ca else "")
    with requests.Session() as session:
        session.trust_env = False
        client = ProxmoxApiClient(config, session)
        for request in (client.get_version, client.get_nodes):
            with pytest.raises(ProxmoxApiError, match="PVE TLS verification failed") as error:
                request()
            assert config.pve_api_token_secret not in str(error.value)
        status = PveService(config, client).status()
        assert status["reachable"] is False
        assert "PVE TLS verification failed" in status["error"]
    assert calls == []  # No HTTP request, including credentials, crossed the failed handshake.
    assert config.pve_verify_ssl is True


def test_trusted_matching_cert_succeeds(https_server, certificates: dict[str, Path]) -> None:
    url, calls = https_server()
    with requests.Session() as session:
        session.trust_env = False
        client = ProxmoxApiClient(settings(pve_url=url, pve_ca_bundle=str(certificates["ca"])), session)
        assert client.get_version() == {"version": "synthetic"}
        assert client.get_nodes() == []
    assert calls == ["/api2/json/version", "/api2/json/nodes"]


def test_secure_mode_rejects_plain_http() -> None:
    with pytest.raises(ProxmoxApiError, match="PVE_URL must use HTTPS"):
        ProxmoxApiClient(settings(pve_url="http://127.0.0.1")).get_version()


def test_settings_are_isolated_and_bool_remains_bool(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PVE_VERIFY_SSL", "false")
    monkeypatch.setenv("PVE_CA_BUNDLE", "caller-private-path")
    (tmp_path / ".env").write_text("PVE_VERIFY_SSL=false\nBACKEND_WORKERS=invalid\n")
    assert settings().pve_verify_ssl is True
    assert settings().pve_ca_bundle == ""
    assert settings(pve_verify_ssl="false").pve_tls_verify() is False
    with pytest.raises(ValueError):
        settings(pve_verify_ssl="/path/to/ca.pem")
