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

    def container_stats(self) -> list[dict[str, Any]]:
        containers = self.client.get_containers()
        active = [item for item in containers if item.get("State") == "running"]
        results: list[dict[str, Any]] = []
        for container in active[: self.client.settings.docker_stats_limit]:
            container_id = str(container.get("Id", ""))
            if not container_id:
                continue
            try:
                stats = self.client.get_container_stats(container_id)
            except Exception:  # noqa: BLE001
                continue
            results.append({"id": container_id, **self._normalize_stats(stats)})
        return results

    @staticmethod
    def _normalize_stats(stats: dict[str, Any]) -> dict[str, float | int]:
        cpu = stats.get("cpu_stats", {})
        previous_cpu = stats.get("precpu_stats", {})
        cpu_delta = float(cpu.get("cpu_usage", {}).get("total_usage", 0)) - float(
            previous_cpu.get("cpu_usage", {}).get("total_usage", 0)
        )
        system_delta = float(cpu.get("system_cpu_usage", 0)) - float(previous_cpu.get("system_cpu_usage", 0))
        online_cpus = int(cpu.get("online_cpus") or len(cpu.get("cpu_usage", {}).get("percpu_usage", []) or []) or 1)
        cpu_percent = (cpu_delta / system_delta) * online_cpus * 100 if system_delta > 0 else 0.0
        memory = stats.get("memory_stats", {})
        memory_usage = float(memory.get("usage", 0))
        memory_limit = float(memory.get("limit", 0))
        networks = stats.get("networks", {})
        network_rx = sum(float(item.get("rx_bytes", 0)) for item in networks.values() if isinstance(item, dict))
        network_tx = sum(float(item.get("tx_bytes", 0)) for item in networks.values() if isinstance(item, dict))
        return {
            "cpu_percent": round(cpu_percent, 2),
            "memory_usage": int(memory_usage),
            "memory_limit": int(memory_limit),
            "memory_percent": round((memory_usage / memory_limit) * 100, 2) if memory_limit else 0.0,
            "network_rx": int(network_rx),
            "network_tx": int(network_tx),
        }

    def images(self) -> list[dict[str, Any]]:
        return self.client.get_images()

    def volumes(self) -> list[dict[str, Any]]:
        return self.client.get_volumes()
