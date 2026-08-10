from typing import Any

from app.core.config.settings import Settings
from app.core.infrastructure_health.schemas import InfrastructureHealthRead
from app.core.time import utcnow
from app.plugins.docker.application.service import DockerService
from app.plugins.pve.application.service import PveService


class InfrastructureHealthService:
    """Build one consistent, read-only health view for infrastructure plugins."""

    def __init__(self, settings: Settings) -> None:
        self._docker = DockerService(settings)
        self._pve = PveService(settings)

    def check(self) -> InfrastructureHealthRead:
        docker = self._docker.status()
        pve = self._pve.status()
        alerts = self._build_alerts(docker=docker, pve=pve)
        configured = [item for item in (docker, pve) if item["configured"]]
        reachable = [item for item in configured if item["reachable"]]
        return InfrastructureHealthRead(
            checked_at=utcnow(),
            healthy=not alerts,
            configured_components=len(configured),
            reachable_components=len(reachable),
            alerts=alerts,
            docker=docker,
            pve=pve,
        )

    @staticmethod
    def _build_alerts(*, docker: dict[str, Any], pve: dict[str, Any]) -> list[str]:
        alerts: list[str] = []
        if docker["configured"] and not docker["reachable"]:
            alerts.append("Docker 连接异常")
        if docker["configured"] and docker["problematic"]:
            alerts.append(f"{docker['problematic']} 个 Docker 容器异常")
        if pve["configured"] and not pve["reachable"]:
            alerts.append("PVE 连接异常")
        return alerts

