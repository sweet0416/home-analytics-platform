from typing import Any

from app.core.config.settings import Settings
from app.plugins.docker.infrastructure.docker_api import DockerApiClient


class DockerService:
    def __init__(self, settings: Settings, client: DockerApiClient | None = None) -> None:
        self.client = client or DockerApiClient(settings)

    def status(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "plugin": "docker",
            "version": "0.1.0",
            "enabled": self.client.settings.docker_enabled,
            "configured": self.client.configured,
            "reachable": False,
            "docker_version": None,
            "containers": 0,
            "running": 0,
            "error": None,
        }
        if not self.client.configured:
            return result
        try:
            version = self.client.get_version()
            containers = self.client.get_containers()
        except Exception as exc:  # noqa: BLE001
            result["error"] = str(exc)
            return result
        result["reachable"] = True
        result["docker_version"] = version.get("Version")
        result["containers"] = len(containers)
        result["running"] = sum(item.get("State") == "running" for item in containers)
        return result

    def containers(self) -> list[dict[str, Any]]:
        return self.client.get_containers()

    def images(self) -> list[dict[str, Any]]:
        return self.client.get_images()

    def volumes(self) -> list[dict[str, Any]]:
        return self.client.get_volumes()
