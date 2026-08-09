from typing import Any

import pytest

from app.core.config.settings import Settings
from app.plugins.docker.application.service import DockerService
from app.plugins.docker.infrastructure.docker_api import DockerApiClient, DockerApiError


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self.payload


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        if url.endswith("/version"):
            return FakeResponse({"Version": "27.5.1"})
        if "/containers/json" in url:
            return FakeResponse([{"Id": "abc", "State": "running"}, {"Id": "def", "State": "exited"}])
        if url.endswith("/images/json"):
            return FakeResponse([{"Id": "sha256:image"}])
        return FakeResponse({"Volumes": [{"Name": "hap_data", "Driver": "local"}]})


def configured_settings() -> Settings:
    return Settings(docker_enabled=True, docker_url="http://proxy:2375", docker_timeout_seconds=7)


def test_docker_client_reads_only_expected_resources() -> None:
    session = FakeSession()
    client = DockerApiClient(configured_settings(), session=session)  # type: ignore[arg-type]

    assert client.get_version() == {"Version": "27.5.1"}
    assert client.get_containers()[0]["State"] == "running"
    assert client.get_images() == [{"Id": "sha256:image"}]
    assert client.get_volumes() == [{"Name": "hap_data", "Driver": "local"}]
    assert all(call["url"].startswith("http://proxy:2375/") for call in session.calls)
    assert all(call["timeout"] == 7 for call in session.calls)


def test_docker_service_reports_running_count() -> None:
    client = DockerApiClient(configured_settings(), session=FakeSession())  # type: ignore[arg-type]

    result = DockerService(configured_settings(), client=client).status()

    assert result["reachable"] is True
    assert result["docker_version"] == "27.5.1"
    assert result["containers"] == 2
    assert result["running"] == 1


def test_docker_client_rejects_unconfigured_access() -> None:
    client = DockerApiClient(Settings())

    with pytest.raises(DockerApiError, match="not configured"):
        client.get_containers()


def test_docker_client_rejects_invalid_volumes() -> None:
    class InvalidVolumeSession(FakeSession):
        def get(self, url: str, **kwargs: Any) -> FakeResponse:
            return FakeResponse({"Volumes": {"invalid": True}})

    client = DockerApiClient(configured_settings(), session=InvalidVolumeSession())  # type: ignore[arg-type]

    with pytest.raises(DockerApiError, match="invalid volume list"):
        client.get_volumes()
