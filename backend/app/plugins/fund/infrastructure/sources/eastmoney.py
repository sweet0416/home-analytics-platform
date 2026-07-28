import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

import requests

from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


@dataclass(frozen=True)
class FundLatestNav:
    fund_code: str
    fund_name: str
    fund_type: str
    nav_date: date
    unit_nav: Decimal
    accumulated_nav: Decimal | None
    source: str
    source_url: str


class EastmoneyFundNavSource:
    source = "eastmoney"
    default_url_template = "https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
    referer_template = "https://fund.eastmoney.com/{fund_code}.html"

    def __init__(
        self,
        timeout_seconds: int = 20,
        url_template: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.url_template = url_template or self.default_url_template
        self.session = session or requests.Session()

    def fetch_latest(self, fund_code: str, fund_type: str = "unknown") -> FundLatestNav:
        normalized_code = fund_code.strip()
        source_url = self._build_source_url(normalized_code)
        try:
            response = self.session.get(
                source_url,
                headers={
                    "Accept": "*/*",
                    "Referer": self.referer_template.format(fund_code=normalized_code),
                    "User-Agent": "Mozilla/5.0 HAP/1.1",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise AppError(
                code=ErrorCode.fund_nav_source_unavailable,
                message=f"Eastmoney fund NAV source is unavailable: {exc}",
                status_code=502,
            ) from exc

        try:
            return self.parse_script(
                response.text,
                source_url=response.url,
                fund_code=normalized_code,
                fund_type=fund_type,
            )
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                code=ErrorCode.fund_nav_parse_failed,
                message=f"Eastmoney fund NAV response could not be parsed: {exc}",
                status_code=502,
            ) from exc

    def parse_script(
        self,
        content: str,
        *,
        source_url: str,
        fund_code: str,
        fund_type: str,
    ) -> FundLatestNav:
        parsed_code = self._extract_string(content, "fS_code") or fund_code
        fund_name = self._extract_string(content, "fS_name")
        if not fund_name:
            raise AppError(
                code=ErrorCode.fund_nav_parse_failed,
                message="Eastmoney response did not include fund name.",
                status_code=502,
            )

        net_worth = self._extract_json_assignment(content, "Data_netWorthTrend")
        if not net_worth:
            raise AppError(
                code=ErrorCode.fund_nav_parse_failed,
                message="Eastmoney response did not include unit NAV trend.",
                status_code=502,
            )
        latest = max(net_worth, key=lambda item: int(item["x"]))
        timestamp = int(latest["x"])
        nav_date = datetime.fromtimestamp(timestamp / 1000, tz=UTC).date()
        unit_nav = self._parse_decimal(latest["y"])

        accumulated_nav = self._extract_accumulated_nav(content, timestamp)
        return FundLatestNav(
            fund_code=parsed_code,
            fund_name=fund_name,
            fund_type=fund_type or "unknown",
            nav_date=nav_date,
            unit_nav=unit_nav,
            accumulated_nav=accumulated_nav,
            source=self.source,
            source_url=source_url,
        )

    def _build_source_url(self, fund_code: str) -> str:
        separator = "&" if "?" in self.url_template else "?"
        return f"{self.url_template.format(fund_code=fund_code)}{separator}v={int(time.time() * 1000)}"

    @staticmethod
    def _extract_string(content: str, variable_name: str) -> str | None:
        match = re.search(rf"var\s+{re.escape(variable_name)}\s*=\s*['\"]([^'\"]+)['\"]", content)
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_json_assignment(content: str, variable_name: str) -> list[dict[str, object]]:
        match = re.search(
            rf"var\s+{re.escape(variable_name)}\s*=\s*(\[.*?\]);",
            content,
            flags=re.DOTALL,
        )
        if not match:
            return []
        return json.loads(match.group(1))

    def _extract_accumulated_nav(self, content: str, timestamp: int) -> Decimal | None:
        rows = self._extract_json_assignment(content, "Data_ACWorthTrend")
        if not rows:
            return None
        exact = [row for row in rows if isinstance(row, list) and row and int(row[0]) == timestamp]
        selected = exact[0] if exact else max(
            (row for row in rows if isinstance(row, list) and len(row) >= 2),
            key=lambda row: int(row[0]),
        )
        return self._parse_decimal(selected[1])

    @staticmethod
    def _parse_decimal(value: object) -> Decimal:
        try:
            return Decimal(str(value)).quantize(Decimal("0.0001"))
        except (InvalidOperation, ValueError) as exc:
            raise AppError(
                code=ErrorCode.fund_nav_parse_failed,
                message=f"Fund NAV value could not be parsed: {value}",
                status_code=502,
            ) from exc
