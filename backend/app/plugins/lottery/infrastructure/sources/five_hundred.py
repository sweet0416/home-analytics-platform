import re
from datetime import date
from decimal import Decimal, InvalidOperation

import requests
from bs4 import BeautifulSoup, Tag

from app.plugins.lottery.domain.constants import DLT_GAME_CODE
from app.plugins.lottery.domain.sync import DrawRecord, DrawSourcePage
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


class FiveHundredDrawSource:
    source = "500_lottery"
    base_url = "https://datachart.500.com/dlt/history/newinc/history.php"
    referer = "https://datachart.500.com/dlt/history/history.shtml"

    def __init__(
        self,
        timeout_seconds: int = 30,
        base_url: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url or type(self).base_url
        self.session = session or requests.Session()

    def fetch_page(self, page: int, page_size: int) -> DrawSourcePage:
        requested_limit = page * page_size
        params = {"limit": requested_limit, "sort": 0}
        try:
            response = self.session.get(
                self.base_url,
                params=params,
                headers={
                    "Accept": "text/html,application/xhtml+xml",
                    "Referer": self.referer,
                    "User-Agent": "Mozilla/5.0 HAP/1.1",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise AppError(
                code=ErrorCode.lottery_sync_source_unavailable,
                message=f"500 Lottery source is unavailable: {exc}",
                status_code=502,
            ) from exc

        source_url = response.url
        try:
            records = self.parse_html(response.content, source_url)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                code=ErrorCode.lottery_sync_parse_failed,
                message=f"500 Lottery response could not be parsed: {exc}",
                status_code=502,
            ) from exc
        start = (page - 1) * page_size
        selected_records = records[start : start + page_size]
        if not selected_records:
            raise AppError(
                code=ErrorCode.lottery_sync_parse_failed,
                message=f"500 Lottery returned no records for page {page}.",
                status_code=502,
            )

        return DrawSourcePage(
            source=self.source,
            source_url=source_url,
            records=selected_records,
            raw_metadata={
                "page": page,
                "page_size": page_size,
                "requested_limit": requested_limit,
                "parsed_count": len(records),
                "provider_type": "third_party_fallback",
            },
        )

    def parse_html(self, content: bytes | str, source_url: str) -> list[DrawRecord]:
        soup = BeautifulSoup(content, "html.parser")
        table = soup.select_one("#tablelist")
        rows = table.select("tr") if table is not None else soup.select("tr")
        records = [record for row in rows if (record := self._parse_row(row, source_url))]
        if not records:
            raise AppError(
                code=ErrorCode.lottery_sync_parse_failed,
                message="500 Lottery response did not contain DLT draw rows.",
                status_code=502,
            )
        return records

    def _parse_row(self, row: Tag, source_url: str) -> DrawRecord | None:
        values = [cell.get_text(strip=True) for cell in row.select("td")]
        if len(values) < 15 or re.fullmatch(r"\d{5}", values[0]) is None:
            return None

        try:
            front_numbers = sorted(int(value) for value in values[1:6])
            back_numbers = sorted(int(value) for value in values[6:8])
            draw_date = date.fromisoformat(values[14])
        except (TypeError, ValueError) as exc:
            raise AppError(
                code=ErrorCode.lottery_sync_parse_failed,
                message=f"500 Lottery draw row could not be parsed: {values[0]}",
                status_code=502,
            ) from exc

        return DrawRecord(
            game_code=DLT_GAME_CODE,
            issue_no=values[0],
            draw_date=draw_date,
            front_numbers=front_numbers,
            back_numbers=back_numbers,
            pool_amount=self._parse_decimal(values[8]),
            sales_amount=self._parse_decimal(values[13]),
            source_url=source_url,
            raw_data={
                "issue_no": values[0],
                "first_prize_winner_count": values[9],
                "first_prize_amount": values[10],
                "second_prize_winner_count": values[11],
                "second_prize_amount": values[12],
                "provider": self.source,
            },
        )

    @staticmethod
    def _parse_decimal(value: str) -> Decimal | None:
        normalized = re.sub(r"[^\d.]", "", value)
        if not normalized:
            return None
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return None
