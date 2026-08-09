from typing import Any

import requests

from app.core.config.settings import Settings


class ProxmoxApiError(RuntimeError):
    """Raised when the PVE API cannot be reached or returns an error."""


class ProxmoxApiClient:
    def __init__(self, settings: Settings, session: requests.Session | None = None) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self.base_url = settings.pve_url.rstrip("/")
        self.session.headers.update(
            {"Authorization": f"PVEAPIToken={settings.pve_api_token_id}={settings.pve_api_token_secret}"}
        )

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.pve_enabled
            and self.base_url
            and self.settings.pve_api_token_id
            and self.settings.pve_api_token_secret
        )

    def get_version(self) -> dict[str, Any]:
        return self._get("/version")

    def get_nodes(self) -> list[dict[str, Any]]:
        return self._get_list("/nodes")

    def get_guests(self) -> list[dict[str, Any]]:
        return self._get_list("/cluster/resources?type=vm")

    def get_storage(self) -> list[dict[str, Any]]:
        try:
            resources = self._get_list("/cluster/resources?type=storage")
        except ProxmoxApiError:
            return self._get_list("/storage")
        return [self._normalize_storage(item) for item in resources]

    def get_tasks(self, limit: int) -> list[dict[str, Any]]:
        return self._get_list(f"/cluster/tasks?limit={limit}")

    def get_node_tasks(self, node: str, limit: int) -> list[dict[str, Any]]:
        return self._get_list(f"/nodes/{node}/tasks?limit={limit}")

    @staticmethod
    def _normalize_storage(item: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(item)
        if "used" not in normalized and "disk" in normalized:
            normalized["used"] = normalized["disk"]
        if "total" not in normalized and "maxdisk" in normalized:
            normalized["total"] = normalized["maxdisk"]
        return normalized

    def _get(self, path: str) -> dict[str, Any]:
        if not self.configured:
            raise ProxmoxApiError("PVE monitoring is not configured.")
        try:
            response = self.session.get(
                f"{self.base_url}/api2/json{path}",
                timeout=self.settings.pve_timeout_seconds,
                verify=self.settings.pve_verify_ssl,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ProxmoxApiError(str(exc)) from exc
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ProxmoxApiError("PVE API returned an invalid object.")
        return data

    def _get_list(self, path: str) -> list[dict[str, Any]]:
        if not self.configured:
            raise ProxmoxApiError("PVE monitoring is not configured.")
        try:
            response = self.session.get(
                f"{self.base_url}/api2/json{path}",
                timeout=self.settings.pve_timeout_seconds,
                verify=self.settings.pve_verify_ssl,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ProxmoxApiError(str(exc)) from exc
        data = payload.get("data")
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise ProxmoxApiError("PVE API returned an invalid list.")
        return data
