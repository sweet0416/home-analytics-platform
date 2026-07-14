from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol

from app.plugins.lottery.domain.constants import DLT_GAME_CODE
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


@dataclass(frozen=True)
class DrawRecord:
    game_code: str
    issue_no: str
    draw_date: date
    front_numbers: list[int]
    back_numbers: list[int]
    sales_amount: Decimal | None = None
    pool_amount: Decimal | None = None
    source_url: str | None = None
    raw_data: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class DrawSourcePage:
    source: str
    source_url: str
    records: list[DrawRecord]
    raw_metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class DrawSyncCommand:
    sync_type: str = "manual"
    page: int = 1
    page_size: int = 100
    force: bool = False


class DrawSource(Protocol):
    source: str
    base_url: str

    def fetch_page(self, page: int, page_size: int) -> DrawSourcePage: ...


class DrawValidator:
    def validate_dlt_record(self, record: DrawRecord) -> None:
        if record.game_code != DLT_GAME_CODE:
            self._raise(f"Unsupported game code: {record.game_code}")
        if not record.issue_no.strip():
            self._raise("Issue number is required.")
        if len(record.front_numbers) != 5:
            self._raise("DLT front area must contain exactly 5 numbers.")
        if len(record.back_numbers) != 2:
            self._raise("DLT back area must contain exactly 2 numbers.")
        if len(set(record.front_numbers)) != len(record.front_numbers):
            self._raise("DLT front area contains duplicated numbers.")
        if len(set(record.back_numbers)) != len(record.back_numbers):
            self._raise("DLT back area contains duplicated numbers.")
        if record.front_numbers != sorted(record.front_numbers):
            self._raise("DLT front area numbers must be sorted.")
        if record.back_numbers != sorted(record.back_numbers):
            self._raise("DLT back area numbers must be sorted.")
        if any(number < 1 or number > 35 for number in record.front_numbers):
            self._raise("DLT front area number is out of range.")
        if any(number < 1 or number > 12 for number in record.back_numbers):
            self._raise("DLT back area number is out of range.")

    @staticmethod
    def _raise(message: str) -> None:
        raise AppError(
            code=ErrorCode.lottery_sync_validation_failed,
            message=message,
            status_code=400,
        )
