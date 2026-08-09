from typing import Any

from pydantic import BaseModel, ConfigDict


class PveStatusRead(BaseModel):
    plugin: str
    version: str
    enabled: bool
    configured: bool
    reachable: bool
    pve_version: str | None = None
    error: str | None = None


class PveResourceRead(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: list[dict[str, Any]]
