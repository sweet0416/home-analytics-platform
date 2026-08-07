from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.plugins.fund.infrastructure.sources.eastmoney import FundLatestNav
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


@dataclass(frozen=True)
class TtSkillBaseInfoSource:
    source: str = "ttfund_skills"
    source_url: str = "ttskill://TTFUND_BASE_INFOS/query_by_code"

    def parse(self, payload: dict[str, Any]) -> FundLatestNav:
        data = _mapping(payload.get("data"), "data")
        if payload.get("code") != 0 or data.get("skill_id") != "TTFUND_BASE_INFOS":
            _raise_parse_error("Unexpected Tiantian Skills response envelope.")

        raw_result = _mapping(data.get("raw_result"), "data.raw_result")
        body = _mapping(raw_result.get("body"), "data.raw_result.body")
        rows = body.get("data")
        if raw_result.get("status_code") != 200 or body.get("success") is not True:
            _raise_parse_error("Tiantian Skills upstream request was not successful.")
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            _raise_parse_error("Tiantian Skills response must contain exactly one fund.")

        row = rows[0]
        return FundLatestNav(
            fund_code=_required_text(row.get("FCODE"), "FCODE"),
            fund_name=_required_text(row.get("SHORTNAME"), "SHORTNAME"),
            fund_type=_text(row.get("FTYPE")) or "unknown",
            nav_date=_required_date(row.get("FSRQ"), "FSRQ"),
            unit_nav=_required_decimal(row.get("DWJZ"), "DWJZ"),
            accumulated_nav=_decimal(row.get("LJJZ")),
            source=self.source,
            source_url=self.source_url,
        )


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _raise_parse_error(f"Tiantian Skills response is missing {field}.")
    return value


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _required_text(value: object, field: str) -> str:
    text = _text(value)
    if text is None:
        _raise_parse_error(f"Tiantian Skills response is missing {field}.")
    return text


def _required_date(value: object, field: str) -> date:
    text = _required_text(value, field)
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        _raise_parse_error(f"Tiantian Skills field {field} is not a valid date.")


def _decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.0001"))
    except (InvalidOperation, ValueError):
        return None


def _required_decimal(value: object, field: str) -> Decimal:
    parsed = _decimal(value)
    if parsed is None or parsed <= 0:
        _raise_parse_error(f"Tiantian Skills field {field} is not a positive number.")
    return parsed


def _raise_parse_error(message: str) -> None:
    raise AppError(
        code=ErrorCode.fund_ttskill_parse_failed,
        message=message,
        status_code=422,
    )
