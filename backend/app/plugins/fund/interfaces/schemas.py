from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class FundPositionCreate(BaseModel):
    fund_code: str = Field(min_length=1, max_length=16)
    fund_name: str = Field(min_length=1, max_length=128)
    fund_type: str = Field(default="unknown", max_length=64)
    account_name: str = Field(default="默认账户", max_length=64)
    shares: Decimal = Field(gt=0, decimal_places=4)
    cost_price: Decimal = Field(gt=0, decimal_places=4)
    total_cost: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    current_nav: Decimal | None = Field(default=None, gt=0, decimal_places=4)
    opened_at: date | None = None
    tags: str = Field(default="", max_length=256)
    note: str = ""

    @field_validator("fund_code", "fund_name", "fund_type", "account_name", "tags", "note")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @property
    def normalized_total_cost(self) -> Decimal:
        value = self.total_cost if self.total_cost is not None else self.shares * self.cost_price
        return value.quantize(Decimal("0.01"))


class FundPositionRead(BaseModel):
    id: int
    fund_id: int
    fund_code: str
    fund_name: str
    fund_type: str
    account_name: str
    shares: Decimal
    cost_price: Decimal
    total_cost: Decimal
    current_nav: Decimal | None
    current_value: Decimal | None
    unrealized_profit: Decimal | None
    unrealized_return_rate: Decimal | None
    opened_at: date | None
    tags: str
    note: str
    created_at: datetime
    updated_at: datetime


class FundHoldingSummaryRead(BaseModel):
    position_count: int
    fund_count: int
    total_cost: Decimal
    current_value: Decimal | None
    unrealized_profit: Decimal | None
    unrealized_return_rate: Decimal | None
    valued_position_count: int
    fund_types: list[str]
    accounts: list[str]


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
