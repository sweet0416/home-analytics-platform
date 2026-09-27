from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.plugins.docker.interfaces.schemas import DockerStatusRead
from app.plugins.pve.interfaces.schemas import PveStatusRead


class InfrastructureHealthRead(BaseModel):
    checked_at: datetime
    healthy: bool
    configured_components: int
    reachable_components: int
    alerts: list[str]
    docker: DockerStatusRead
    pve: PveStatusRead


class InfrastructureNotificationState(BaseModel):
    """Only conditions already used by the health evaluator; never display copy."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    version: Literal[1] = 1
    docker_unreachable: bool
    docker_problematic: int = Field(ge=0)
    pve_unreachable: bool

    @property
    def healthy(self) -> bool:
        return not (self.docker_unreachable or self.docker_problematic or self.pve_unreachable)

    @classmethod
    def from_health(cls, health: InfrastructureHealthRead) -> "InfrastructureNotificationState":
        return cls(
            docker_unreachable=health.docker.configured and not health.docker.reachable,
            docker_problematic=health.docker.problematic if health.docker.configured else 0,
            pve_unreachable=health.pve.configured and not health.pve.reachable,
        )

