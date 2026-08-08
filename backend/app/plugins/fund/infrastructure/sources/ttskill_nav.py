from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.plugins.fund.infrastructure.sources.eastmoney import FundLatestNav
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


@dataclass(frozen=True)
class TtSkillNavInfoSource:
    source: str = "ttfund_skills"
    source_url: str = "ttskill://TTFUND_NAV_INFO/query"

    def parse(self, payload: dict[str, Any]) -> FundLatestNav:
        data = self._mapping(payload.get("data"), "data")
        if payload.get("code") != 0 or data.get("skill_id") != "TTFUND_NAV_INFO":
            self._raise("Unexpected Tiantian NAV Skills response envelope.")
        raw = self._mapping(data.get("raw_result"), "data.raw_result")
        body = self._mapping(raw.get("body"), "data.raw_result.body")
        if raw.get("status_code") != 200 or body.get("success") is not True:
            self._raise("Tiantian NAV Skills request was not successful.")
        # Installed NAV_INFO skill versions may return different action labels
        # (for example query/query_by_code); the skill id and data contract are
        # the stable identifiers for this protected endpoint.
        result = self._mapping(body.get("data"), "data.raw_result.body.data")
        profile = self._mapping(result.get("fund_profile"), "fund_profile")
        history = self._mapping(result.get("nav_history"), "nav_history")
        item = self._latest_item(history.get("items"))
        code = profile.get("fund_code") or profile.get("input_fund_id")
        return FundLatestNav(
            fund_code=self._required_text(code, "fund_code"),
            fund_name=self._required_text(profile.get("fund_name"), "fund_name"),
            fund_type=self._text(profile.get("fund_type")) or "unknown",
            nav_date=self._required_date(item.get("FSRQ"), "FSRQ"),
            unit_nav=self._required_decimal(item.get("DWJZ"), "DWJZ"),
            accumulated_nav=self._decimal(item.get("LJJZ")),
            source=self.source,
            source_url=self.source_url,
        )

    @classmethod
    def _latest_item(cls, value: object) -> dict[str, Any]:
        if isinstance(value, list):
            rows = [row for row in value if isinstance(row, dict)]
            if rows:
                return max(rows, key=lambda row: str(row.get("FSRQ") or ""))
        if isinstance(value, dict):
            dates = value.get("FSRQ")
            units = value.get("DWJZ")
            accumulated = value.get("LJJZ")
            if isinstance(dates, list) and isinstance(units, list):
                rows = [
                    {
                        "FSRQ": item_date,
                        "DWJZ": units[index],
                        "LJJZ": accumulated[index]
                        if isinstance(accumulated, list) and index < len(accumulated)
                        else None,
                    }
                    for index, item_date in enumerate(dates)
                    if index < len(units)
                ]
                if rows:
                    return max(rows, key=lambda row: str(row.get("FSRQ") or ""))
        cls._raise("Tiantian NAV Skills response is missing nav_history.items.")

    @staticmethod
    def _mapping(value: object, field: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            TtSkillNavInfoSource._raise(f"Tiantian NAV Skills response is missing {field}.")
        return value

    @staticmethod
    def _text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @classmethod
    def _required_text(cls, value: object, field: str) -> str:
        text = cls._text(value)
        if text is None:
            cls._raise(f"Tiantian NAV Skills response is missing {field}.")
        return text

    @classmethod
    def _required_date(cls, value: object, field: str) -> date:
        text = cls._required_text(value, field)
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            cls._raise(f"Tiantian NAV Skills field {field} is not a valid date.")

    @classmethod
    def _decimal(cls, value: object) -> Decimal | None:
        text = cls._text(value)
        if text is None or text in {"--", "-"}:
            return None
        try:
            return Decimal(text.replace(",", "")).quantize(Decimal("0.0001"))
        except (InvalidOperation, ValueError):
            return None

    @classmethod
    def _required_decimal(cls, value: object, field: str) -> Decimal:
        parsed = cls._decimal(value)
        if parsed is None or parsed <= 0:
            cls._raise(f"Tiantian NAV Skills field {field} is not a positive number.")
        return parsed

    @staticmethod
    def _raise(message: str) -> None:
        raise AppError(code=ErrorCode.fund_ttskill_parse_failed, message=message, status_code=422)
