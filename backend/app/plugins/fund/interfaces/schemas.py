from pydantic import BaseModel


class FundModuleRead(BaseModel):
    code: str
    name: str
    description: str
    status: str


class FundStatusRead(BaseModel):
    plugin: str
    display_name: str
    version: str
    status: str
    description: str
    modules: list[FundModuleRead]
    data_source_status: str
    storage_status: str
    next_step: str
