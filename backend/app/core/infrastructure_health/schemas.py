from datetime import datetime

from pydantic import BaseModel

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

