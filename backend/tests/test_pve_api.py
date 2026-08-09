from typing import Any

import pytest
import requests
from fastapi.testclient import TestClient

from app.core.config.settings import Settings
from app.plugins.pve.application.service import PveService
from app.plugins.pve.infrastructure.proxmox_api import (
    ProxmoxApiClient,
    ProxmoxApiError,
)


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


class FakeSession:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.headers: dict[str, str] = {}
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return FakeResponse(self.payload)


def configured_settings() -> Settings:
    return Settings(
        pve_enabled=True,
        pve_url="https://pve.example.test:8006",
        pve_api_token_id="hap-monitor@pve!readonly",
        pve_api_token_secret="secret-for-test",
        pve_verify_ssl=False,
    )


def test_pve_client_uses_token_and_reads_version() -> None:
    session = FakeSession({"data": {"version": "9.2.10", "release": "1"}})
    client = ProxmoxApiClient(configured_settings(), session=session)  # type: ignore[arg-type]

    assert client.get_version() == {"version": "9.2.10", "release": "1"}
    assert session.headers["Authorization"] == (
        "PVEAPIToken=hap-monitor@pve!readonly=secret-for-test"
    )
    assert session.calls[0]["url"] == "https://pve.example.test:8006/api2/json/version"
    assert session.calls[0]["verify"] is False


def test_pve_client_rejects_unconfigured_access() -> None:
    client = ProxmoxApiClient(Settings())

    with pytest.raises(ProxmoxApiError, match="not configured"):
        client.get_nodes()


def test_pve_service_reports_unreachable_without_leaking_secret() -> None:
    class FailingClient:
        configured = True

        def get_version(self) -> dict[str, Any]:
            raise ProxmoxApiError("connection refused")

    result = PveService(configured_settings(), client=FailingClient()).status()  # type: ignore[arg-type]

    assert result["reachable"] is False
    assert result["error"] == "connection refused"
    assert "secret-for-test" not in str(result)


def test_pve_client_rejects_invalid_list_response() -> None:
    session = FakeSession({"data": {"unexpected": True}})
    client = ProxmoxApiClient(configured_settings(), session=session)  # type: ignore[arg-type]

    with pytest.raises(ProxmoxApiError, match="invalid list"):
        client.get_storage()


def test_pve_client_normalizes_storage_usage() -> None:
    session = FakeSession({"data": [{"storage": "local", "disk": 25, "maxdisk": 100}]})
    client = ProxmoxApiClient(configured_settings(), session=session)  # type: ignore[arg-type]

    assert client.get_storage() == [
        {"storage": "local", "disk": 25, "maxdisk": 100, "used": 25, "total": 100}
    ]


def test_pve_client_translates_request_errors() -> None:
    class ErrorSession(FakeSession):
        def get(self, url: str, **kwargs: Any) -> FakeResponse:
            raise requests.Timeout("timed out")

    client = ProxmoxApiClient(configured_settings(), session=ErrorSession({}))  # type: ignore[arg-type]

    with pytest.raises(ProxmoxApiError, match="timed out"):
        client.get_version()


def test_pve_service_falls_back_to_node_tasks() -> None:
    class TaskFallbackClient:
        configured = True

        def get_tasks(self, limit: int) -> list[dict[str, Any]]:
            raise ProxmoxApiError("cluster tasks forbidden")

        def get_nodes(self) -> list[dict[str, Any]]:
            return [{"node": "VUModule"}]

        def get_node_tasks(self, node: str, limit: int) -> list[dict[str, Any]]:
            assert node == "VUModule"
            return [{"node": node, "status": "OK"}]

    result = PveService(configured_settings(), client=TaskFallbackClient()).tasks()  # type: ignore[arg-type]

    assert result == [{"node": "VUModule", "status": "OK"}]


def test_pve_status_is_explicit_when_disabled(client: TestClient) -> None:
    response = client.get("/api/v1/pve/status")

    assert response.status_code == 200
    assert response.json()["data"] == {
        "plugin": "pve",
        "version": "0.1.0",
        "enabled": False,
        "configured": False,
        "reachable": False,
        "pve_version": None,
        "error": None,
    }


def test_pve_data_endpoint_reports_not_configured(client: TestClient) -> None:
    response = client.get("/api/v1/pve/nodes")

    assert response.status_code == 503
    assert response.json()["code"] == "PVE_NOT_CONFIGURED"
