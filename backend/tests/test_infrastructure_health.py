from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from app.core.config.settings import Settings
from app.core.infrastructure_health.scheduler import build_health_notification_message
from app.core.infrastructure_health.service import InfrastructureHealthService


def _status(*, configured: bool, reachable: bool, problematic: int = 0) -> dict[str, Any]:
    return {
        "plugin": "test",
        "version": "0.1.0",
        "enabled": configured,
        "configured": configured,
        "reachable": reachable,
        "docker_version": "25.0.5" if configured else None,
        "containers": 3,
        "running": 3,
        "problematic": problematic,
        "error": None if reachable else "connection refused",
    }


def test_infrastructure_health_is_healthy_when_configured_services_are_reachable(monkeypatch) -> None:
    service = InfrastructureHealthService(Settings())
    monkeypatch.setattr(service._docker, "status", lambda: _status(configured=True, reachable=True))
    monkeypatch.setattr(service._pve, "status", lambda: {
        "plugin": "pve",
        "version": "0.1.0",
        "enabled": True,
        "configured": True,
        "reachable": True,
        "pve_version": "9.2.10",
        "error": None,
    })

    result = service.check()

    assert result.healthy is True
    assert result.configured_components == 2
    assert result.reachable_components == 2
    assert result.alerts == []


def test_infrastructure_health_reports_connection_and_container_alerts(monkeypatch) -> None:
    service = InfrastructureHealthService(Settings())
    monkeypatch.setattr(service._docker, "status", lambda: _status(configured=True, reachable=False, problematic=2))
    monkeypatch.setattr(service._pve, "status", lambda: {
        "plugin": "pve",
        "version": "0.1.0",
        "enabled": True,
        "configured": True,
        "reachable": False,
        "pve_version": None,
        "error": "certificate verify failed",
    })

    result = service.check()

    assert result.healthy is False
    assert result.reachable_components == 0
    assert result.alerts == ["Docker 连接异常", "2 个 Docker 容器异常", "PVE 连接异常"]


def test_infrastructure_health_ignores_disabled_plugins(monkeypatch) -> None:
    service = InfrastructureHealthService(Settings())
    monkeypatch.setattr(service._docker, "status", lambda: _status(configured=False, reachable=False))
    monkeypatch.setattr(service._pve, "status", lambda: {
        "plugin": "pve",
        "version": "0.1.0",
        "enabled": False,
        "configured": False,
        "reachable": False,
        "pve_version": None,
        "error": None,
    })

    result = service.check()

    assert result.healthy is True
    assert result.configured_components == 0
    assert result.reachable_components == 0
    assert result.alerts == []


def test_infrastructure_health_endpoint_returns_unified_shape(client: TestClient) -> None:
    response = client.get("/api/v1/system/infrastructure-health")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["healthy"] is True
    assert payload["configured_components"] == 0
    assert payload["alerts"] == []
    assert payload["docker"]["plugin"] == "docker"
    assert payload["pve"]["plugin"] == "pve"


def test_health_notification_message_explains_unhealthy_components() -> None:
    health = SimpleNamespace(
        healthy=False,
        alerts=["Docker 连接异常", "1 个 Docker 容器异常"],
        docker=SimpleNamespace(reachable=False, running=2, containers=3, problematic=1),
        pve=SimpleNamespace(reachable=True),
    )

    message = build_health_notification_message(health)

    assert "状态：异常" in message
    assert "Docker：连接异常，容器 2/3，异常 1 个" in message
    assert "PVE：已连接" in message
    assert "Docker 连接异常" in message
