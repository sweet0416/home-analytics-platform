from typing import Any

from app.core.config.settings import Settings
from app.plugins.pve.infrastructure.proxmox_api import ProxmoxApiClient


class PveService:
    def __init__(self, settings: Settings, client: ProxmoxApiClient | None = None) -> None:
        self.settings = settings
        self.client = client or ProxmoxApiClient(settings)

    def status(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "plugin": "pve",
            "version": "0.1.0",
            "enabled": self.settings.pve_enabled,
            "configured": self.client.configured,
            "reachable": False,
            "pve_version": None,
            "error": None,
        }
        if not self.client.configured:
            return result
        try:
            version = self.client.get_version()
        except Exception as exc:  # noqa: BLE001
            result["error"] = str(exc)
            return result
        result["reachable"] = True
        result["pve_version"] = version.get("version")
        return result

    def nodes(self) -> list[dict[str, Any]]:
        return self.client.get_nodes()

    def guests(self) -> list[dict[str, Any]]:
        return self.client.get_guests()

    def storage(self) -> list[dict[str, Any]]:
        return self.client.get_storage()

    def tasks(self) -> list[dict[str, Any]]:
        limit = self.settings.pve_tasks_limit
        try:
            return self.client.get_tasks(limit)
        except Exception:  # noqa: BLE001
            # Some PVE installations restrict the cluster-wide task endpoint.
            # Fall back to the node-scoped read-only endpoint so one limitation
            # does not hide all recent task data.
            tasks: list[dict[str, Any]] = []
            for node in self.client.get_nodes():
                node_name = node.get("node")
                if not isinstance(node_name, str) or not node_name:
                    continue
                try:
                    tasks.extend(self.client.get_node_tasks(node_name, limit))
                except Exception:  # noqa: BLE001
                    continue
                if len(tasks) >= limit:
                    break
            return tasks[:limit]
