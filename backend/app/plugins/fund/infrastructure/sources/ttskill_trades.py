from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


@dataclass(frozen=True)
class TtSkillTrade:
    trade_id: str
    trade_type: str
    fund_code: str
    fund_name: str
    business_type: str
    business_code: str
    trade_time: datetime
    status_text: str
    apply_amount: Decimal | None
    confirm_amount: Decimal | None
    confirm_vol: Decimal | None
    nav: Decimal | None
    confirm_date: date | None
    charge: Decimal
    confirmed: bool
    confirm_status: str

    @property
    def transaction_type(self) -> str | None:
        text = f"{self.business_type} {self.business_code}"
        if "撤单" in text or self.confirm_status == "cancelled":
            return None
        if "分红" in text or self.business_code in {"5", "143", "743"}:
            return "dividend"
        if "卖" in text or self.business_code in {"2", "32"}:
            return "sell"
        if "买" in text or "定投" in text or self.business_code in {"1", "22", "39"}:
            return "buy"
        return None

    @property
    def effective_amount(self) -> Decimal | None:
        return self.confirm_amount or self.apply_amount


@dataclass(frozen=True)
class TtSkillTradeBundle:
    trades: tuple[TtSkillTrade, ...]


class TtSkillTradeQuerySource:
    source = "ttfund_skills"

    def parse_bundle(
        self,
        list_payload: dict[str, Any],
        detail_payloads: list[dict[str, Any]],
    ) -> TtSkillTradeBundle:
        list_rows = self._list_rows(list_payload)
        details = {
            trade.trade_id: trade
            for payload in detail_payloads
            for trade in [self._parse_detail(payload)]
        }
        parsed: list[TtSkillTrade] = []
        for row in list_rows:
            trade_id = self._required_text(
                row.get("tradeId") or row.get("trade_id"), "tradeId"
            )
            detail = details.get(trade_id)
            if detail is None:
                raise self._error(f"Missing trade detail for tradeId {trade_id}.")
            parsed.append(detail)
        return TtSkillTradeBundle(tuple(parsed))

    def _list_rows(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        body = self._response_body(payload, "trade_list")
        result = body.get("trade_list_result") or body.get("tradeListResult")
        if isinstance(result, list):
            rows = result
        elif isinstance(result, dict):
            rows = next(
                (
                    result.get(key)
                    for key in ("trades", "tradeList", "items", "records", "list")
                    if isinstance(result.get(key), list)
                ),
                None,
            )
        else:
            rows = None
        if rows is None:
            rows = self._find_trade_rows(body)
        if rows is None:
            # Some account states return a successful empty result without the
            # result container. Treat it as no trades, not a broken response.
            return []
        return [self._mapping(row, "trade_list_result.trades[]") for row in rows]

    def _parse_detail(self, payload: dict[str, Any]) -> TtSkillTrade:
        body = self._response_body(payload, "trade_detail")
        row = body.get("trade_detail_result") or body.get("tradeDetailResult")
        if not isinstance(row, dict):
            row = self._find_trade_detail(body)
        row = self._mapping(row, "trade_detail_result")
        return TtSkillTrade(
            trade_id=self._required_text(row.get("tradeId"), "tradeId"),
            trade_type=self._required_text(row.get("tradeType"), "tradeType"),
            fund_code=self._required_text(row.get("fundCode"), "fundCode"),
            fund_name=self._required_text(row.get("fundName"), "fundName"),
            business_type=self._text(row.get("businessType")) or "未知",
            business_code=self._text(row.get("businessCode")) or "",
            trade_time=self._required_datetime(row.get("tradeTime"), "tradeTime"),
            status_text=self._text(row.get("statusText")) or "",
            apply_amount=self._money(row.get("applyAmount")),
            confirm_amount=self._money(row.get("confirmAmount")),
            confirm_vol=self._decimal(row.get("confirmVol")),
            nav=self._decimal(row.get("nav")),
            confirm_date=self._date(row.get("confirmDate")),
            charge=self._money(row.get("charge")) or Decimal("0"),
            confirmed=row.get("confirmed") is True,
            confirm_status=self._text(row.get("confirmStatus")) or "unknown",
        )

    def _response_body(self, payload: dict[str, Any], action: str) -> dict[str, Any]:
        data = self._mapping(payload.get("data"), "data")
        raw = self._mapping(data.get("raw_result"), "data.raw_result")
        body = self._mapping(raw.get("body"), "data.raw_result.body")
        if payload.get("code") != 0 or data.get("skill_id") != "TRADE_QUERY":
            raise self._error("Unexpected Tiantian Skills response envelope.")
        if raw.get("status_code") != 200 or body.get("success") is not True:
            raise self._error(f"Tiantian Skills {action} request was not successful.")
        if body.get("action") != action:
            raise self._error(f"Expected Tiantian Skills action {action}.")
        return body

    @staticmethod
    def _mapping(value: object, field: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise TtSkillTradeQuerySource._error(f"Tiantian Skills response is missing {field}.")
        return value

    @classmethod
    def _find_trade_rows(cls, value: object) -> list[object] | None:
        if isinstance(value, list):
            if value and all(isinstance(item, dict) for item in value):
                if any("tradeId" in item or "trade_id" in item for item in value):
                    return value
            for item in value:
                found = cls._find_trade_rows(item)
                if found is not None:
                    return found
        elif isinstance(value, dict):
            for child in value.values():
                found = cls._find_trade_rows(child)
                if found is not None:
                    return found
        return None

    @classmethod
    def _find_trade_detail(cls, value: object) -> dict[str, Any] | None:
        if isinstance(value, dict):
            if "tradeId" in value or "trade_id" in value:
                return value
            for child in value.values():
                found = cls._find_trade_detail(child)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = cls._find_trade_detail(child)
                if found is not None:
                    return found
        return None

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
            raise cls._error(f"Tiantian Skills response is missing {field}.")
        return text

    @classmethod
    def _decimal(cls, value: object) -> Decimal | None:
        text = cls._text(value)
        if text is None or text in {"--", "-"}:
            return None
        try:
            return Decimal(text.replace(",", "").replace("元", "").strip())
        except (InvalidOperation, ValueError):
            return None

    @classmethod
    def _money(cls, value: object) -> Decimal | None:
        return cls._decimal(value)

    @classmethod
    def _date(cls, value: object) -> date | None:
        text = cls._text(value)
        if not text:
            return None
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None

    @classmethod
    def _required_datetime(cls, value: object, field: str) -> datetime:
        text = cls._required_text(value, field)
        try:
            return datetime.fromisoformat(text.replace(" ", "T"))
        except ValueError as exc:
            raise cls._error(f"Tiantian Skills field {field} is not a valid datetime.") from exc

    @staticmethod
    def _error(message: str) -> AppError:
        return AppError(
            code=ErrorCode.fund_ttskill_parse_failed,
            message=message,
            status_code=422,
        )
