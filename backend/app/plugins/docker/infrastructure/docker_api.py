from typing import Any

import requests

from app.core.config.settings import Settings


class DockerApiError(RuntimeError):
    """Raised when the read-only Docker API cannot be reached."""


class DockerApiClient:
    def __init__(self, settings: Settings, session: requests.Session | None = None) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self.base_url = settings.docker_url.rstrip("/")

    @property
    def configured(self) -> bool:
        return bool(self.settings.docker_enabled and self.base_url)

    def get_version(self) -> dict[str, Any]:
        return self._get_object("/version")

    def get_info(self) -> dict[str, Any]:
        return self._get_object("/info")

    def get_containers(self) -> list[dict[str, Any]]:
        return self._get_list("/containers/json?all=1")

    def get_images(self) -> list[dict[str, Any]]:
        return self._get_list("/images/json")

    def get_volumes(self) -> list[dict[str, Any]]:
        payload = self._get_object("/volumes")
        volumes = payload.get("Volumes", [])
        if not isinstance(volumes, list) or not all(isinstance(item, dict) for item in volumes):
            raise DockerApiError("Docker API returned an invalid volume list.")
        return volumes

    def _get_object(self, path: str) -> dict[str, Any]:
        payload = self._get_json(path)
        if not isinstance(payload, dict):
            raise DockerApiError("Docker API returned an invalid object.")
        return payload

    def _get_json(self, path: str) -> Any:
        if not self.configured:
            raise DockerApiError("Docker monitoring is not configured.")
        try:
            response = self.session.get(
                f"{self.base_url}{path}",
                timeout=self.settings.docker_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise DockerApiError(str(exc)) from exc
        return payload

    def _get_list(self, path: str) -> list[dict[str, Any]]:
        payload = self._get_json(path)
        if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
            raise DockerApiError("Docker API returned an invalid list.")
        return payload
