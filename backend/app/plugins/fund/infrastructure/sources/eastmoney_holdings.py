import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

import requests
from bs4 import BeautifulSoup, Tag

from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


@dataclass(frozen=True)
class FundDisclosureHolding:
    rank: int
    asset_type: str
    asset_code: str
    asset_name: str
    nav_ratio: Decimal
    reported_quantity: Decimal | None
    reported_market_value: Decimal | None


@dataclass(frozen=True)
class FundHoldingsDisclosure:
    fund_code: str
    fund_name: str
    report_date: date
    report_period: str
    asset_type: str
    source: str
    source_url: str
    holdings: list[FundDisclosureHolding]


class EastmoneyFundHoldingsSource:
    source = "eastmoney"
    default_url_template = (
        "http://fundf10.eastmoney.com/FundArchivesDatas.aspx"
        "?type=jjcc&code={fund_code}&topline=10&year=&month="
    )

    def __init__(
        self,
        timeout_seconds: int = 20,
        url_template: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.url_template = url_template or self.default_url_template
        self.session = session or requests.Session()

    def fetch_latest(self, fund_code: str) -> FundHoldingsDisclosure:
        normalized_code = fund_code.strip()
        source_url = self.url_template.format(fund_code=normalized_code)
        try:
            response = self.session.get(
                source_url,
                headers={
                    "Accept": "text/html,application/xhtml+xml",
                    "Referer": (
                        "http://fundf10.eastmoney.com/"
                        f"ccmx_{normalized_code}.html"
                    ),
                    "User-Agent": "Mozilla/5.0 HAP/1.1",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise AppError(
                code=ErrorCode.fund_holdings_source_unavailable,
                message=f"Eastmoney fund holdings source is unavailable: {exc}",
                status_code=502,
            ) from exc

        try:
            content = self._decode_response(response)
            return self.parse_page(
                content,
                source_url=response.url,
                fund_code=normalized_code,
            )
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                code=ErrorCode.fund_holdings_parse_failed,
                message=f"Eastmoney fund holdings response could not be parsed: {exc}",
                status_code=502,
            ) from exc

    @classmethod
    def parse_page(
        cls,
        content: str,
        *,
        source_url: str,
        fund_code: str,
    ) -> FundHoldingsDisclosure:
        soup = BeautifulSoup(cls._extract_response_html(content), "html.parser")
        disclosures: list[FundHoldingsDisclosure] = []
        for container in soup.select("div.boxitem"):
            if not isinstance(container, Tag):
                continue
            table = container.select_one("table.tzxq")
            heading = container.select_one("h4.t")
            if not isinstance(table, Tag) or not isinstance(heading, Tag):
                continue
            heading_text = cls._normalize_space(heading.get_text(" ", strip=True))
            report_match = re.search(
                r"截止至：\s*(\d{4}-\d{2}-\d{2})",
                heading_text,
            )
            period_match = re.search(r"(\d{4})年([1-4])季度", heading_text)
            if not report_match or not period_match:
                continue

            headers = [
                cls._normalize_header(cell.get_text(" ", strip=True))
                for cell in table.select("thead th")
            ]
            header_indexes = {name: index for index, name in enumerate(headers)}
            required = {"序号", "股票代码", "股票名称", "占净值比例"}
            if not required.issubset(header_indexes):
                continue

            holdings: list[FundDisclosureHolding] = []
            for row in table.select("tbody tr"):
                cells = row.find_all("td")
                if len(cells) < len(headers):
                    continue
                holdings.append(
                    FundDisclosureHolding(
                        rank=int(
                            cells[header_indexes["序号"]].get_text(strip=True)
                        ),
                        asset_type="stock",
                        asset_code=cells[
                            header_indexes["股票代码"]
                        ].get_text(strip=True),
                        asset_name=cells[
                            header_indexes["股票名称"]
                        ].get_text(" ", strip=True),
                        nav_ratio=cls._parse_percent(
                            cells[
                                header_indexes["占净值比例"]
                            ].get_text(strip=True)
                        ),
                        reported_quantity=cls._parse_optional_decimal(
                            cls._cell_text(
                                cells,
                                headers,
                                prefix="持股数",
                            )
                        ),
                        reported_market_value=cls._parse_optional_decimal(
                            cls._cell_text(
                                cells,
                                headers,
                                prefix="持仓市值",
                            )
                        ),
                    )
                )
            if not holdings:
                continue

            name_link = heading.select_one("a")
            fund_name = (
                name_link.get("title")
                if isinstance(name_link, Tag)
                else None
            ) or heading_text.split(f"{period_match.group(1)}年", 1)[0].strip()
            disclosures.append(
                FundHoldingsDisclosure(
                    fund_code=fund_code,
                    fund_name=str(fund_name).strip(),
                    report_date=date.fromisoformat(report_match.group(1)),
                    report_period=(
                        f"{period_match.group(1)}Q{period_match.group(2)}"
                    ),
                    asset_type="stock",
                    source=cls.source,
                    source_url=source_url,
                    holdings=holdings,
                )
            )

        if not disclosures:
            raise AppError(
                code=ErrorCode.fund_holdings_parse_failed,
                message="Eastmoney response did not include a stock disclosure table.",
                status_code=502,
            )
        return max(disclosures, key=lambda item: item.report_date)

    @staticmethod
    def _decode_response(response: requests.Response) -> str:
        try:
            return response.content.decode("utf-8-sig")
        except UnicodeDecodeError:
            encoding = response.apparent_encoding or response.encoding or "utf-8"
            return response.content.decode(encoding)

    @staticmethod
    def _extract_response_html(content: str) -> str:
        match = re.search(
            r'content:"(.*)",arryear:',
            content,
            flags=re.DOTALL,
        )
        if not match:
            return content
        try:
            return json.loads(f'"{match.group(1)}"')
        except json.JSONDecodeError as exc:
            raise AppError(
                code=ErrorCode.fund_holdings_parse_failed,
                message="Eastmoney holdings wrapper could not be decoded.",
                status_code=502,
            ) from exc

    @staticmethod
    def _normalize_space(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _normalize_header(value: str) -> str:
        return re.sub(r"\s+", "", value)

    @classmethod
    def _cell_text(
        cls,
        cells: list[Tag],
        headers: list[str],
        *,
        prefix: str,
    ) -> str:
        index = next(
            (
                item_index
                for item_index, header in enumerate(headers)
                if header.startswith(prefix)
            ),
            -1,
        )
        return cells[index].get_text(strip=True) if index >= 0 else ""

    @staticmethod
    def _parse_percent(value: str) -> Decimal:
        try:
            return (
                Decimal(value.replace("%", "").replace(",", ""))
                / Decimal("100")
            ).quantize(Decimal("0.00000001"))
        except InvalidOperation as exc:
            raise ValueError(f"Invalid holding percentage: {value}") from exc

    @staticmethod
    def _parse_optional_decimal(value: str) -> Decimal | None:
        normalized = value.replace(",", "").strip()
        if not normalized or normalized in {"-", "--"}:
            return None
        try:
            return Decimal(normalized).quantize(Decimal("0.0001"))
        except InvalidOperation:
            return None
