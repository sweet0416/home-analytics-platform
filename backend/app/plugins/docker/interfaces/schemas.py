from typing import Any

from pydantic import BaseModel, ConfigDict


class DockerStatusRead(BaseModel):
    plugin: str
    version: str
    enabled: bool
    configured: bool
    reachable: bool
    docker_version: str | None = None
    containers: int = 0
    running: int = 0
    problematic: int = 0
    error: str | None = None


class DockerResourceRead(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: list[dict[str, Any]]
