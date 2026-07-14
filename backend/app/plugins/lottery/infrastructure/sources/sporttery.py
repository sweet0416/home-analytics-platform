import json
import re
import urllib.parse
import urllib.request
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.plugins.lottery.domain.constants import DLT_GAME_CODE
from app.plugins.lottery.domain.sync import DrawRecord, DrawSourcePage
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


class SportteryDrawSource:
    source = "sporttery"
    base_url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
    referer = "https://www.sporttery.cn/zst/dlt/"

    def __init__(self, timeout_seconds: int = 30) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch_page(self, page: int, page_size: int) -> DrawSourcePage:
        params = {
            "gameNo": "85",
            "provinceId": "0",
            "pageSize": str(page_size),
            "isVerify": "1",
            "pageNo": str(page),
        }
        source_url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            source_url,
            headers={
                "Accept": "application/json,text/plain,*/*",
                "Referer": self.referer,
                "User-Agent": "Mozilla/5.0 HAP/1.1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read().decode("utf-8")
        except Exception as exc:
            raise AppError(
                code=ErrorCode.lottery_sync_source_unavailable,
                message=f"Sporttery source is unavailable: {exc}",
                status_code=502,
            ) from exc

        try:
            raw = json.loads(payload)
            items = self._extract_items(raw)
            records = [self._parse_item(item, source_url) for item in items]
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                code=ErrorCode.lottery_sync_parse_failed,
                message=f"Sporttery response could not be parsed: {exc}",
                status_code=502,
            ) from exc

        return DrawSourcePage(
            source=self.source,
            source_url=source_url,
            records=records,
            raw_metadata={
                "page": page,
                "page_size": page_size,
                "raw_keys": sorted(raw.keys()) if isinstance(raw, dict) else [],
            },
        )

    def _extract_items(self, raw: Any) -> list[dict[str, Any]]:
        if isinstance(raw, dict):
            for key in ("list", "records", "items"):
                value = raw.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            for key in ("value", "data", "result"):
                value = raw.get(key)
                if isinstance(value, dict):
                    extracted = self._extract_items(value)
                    if extracted:
                        return extracted
        raise AppError(
            code=ErrorCode.lottery_sync_parse_failed,
            message="Sporttery response did not contain a draw list.",
            status_code=502,
        )

    def _parse_item(self, item: dict[str, Any], source_url: str) -> DrawRecord:
        issue_no = str(self._first(item, "lotteryDrawNum", "issueNo", "drawNum", "issue") or "")
        draw_date = self._parse_date(
            str(self._first(item, "lotteryDrawTime", "drawDate", "date", "openTime") or "")
        )
        front_numbers, back_numbers = self._parse_numbers(item)
        return DrawRecord(
            game_code=DLT_GAME_CODE,
            issue_no=issue_no,
            draw_date=draw_date,
            front_numbers=front_numbers,
            back_numbers=back_numbers,
            sales_amount=self._parse_decimal(
                self._first(item, "totalSaleAmount", "salesAmount", "saleAmount")
            ),
            pool_amount=self._parse_decimal(
                self._first(item, "poolBalanceAfterdraw", "poolAmount", "prizePool")
            ),
            source_url=source_url,
            raw_data=item,
        )

    def _parse_numbers(self, item: dict[str, Any]) -> tuple[list[int], list[int]]:
        result = self._first(item, "lotteryDrawResult", "drawResult", "result")
        if isinstance(result, str):
            numbers = [int(value) for value in re.findall(r"\d+", result)]
            if len(numbers) >= 7:
                return sorted(numbers[:5]), sorted(numbers[5:7])

        front = self._first(item, "frontNumbers", "frontArea", "redBalls")
        back = self._first(item, "backNumbers", "backArea", "blueBalls")
        if front is not None and back is not None:
            return sorted(self._numbers_from_value(front)), sorted(self._numbers_from_value(back))

        raise AppError(
            code=ErrorCode.lottery_sync_parse_failed,
            message="Sporttery draw numbers could not be parsed.",
            status_code=502,
        )

    @staticmethod
    def _numbers_from_value(value: Any) -> list[int]:
        if isinstance(value, list):
            return [int(item) for item in value]
        if isinstance(value, str):
            return [int(item) for item in re.findall(r"\d+", value)]
        return []

    @staticmethod
    def _parse_date(value: str) -> date:
        match = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", value)
        if not match:
            raise AppError(
                code=ErrorCode.lottery_sync_parse_failed,
                message=f"Sporttery draw date could not be parsed: {value}",
                status_code=502,
            )
        year, month, day = (int(part) for part in match.groups())
        return date(year, month, day)

    @staticmethod
    def _parse_decimal(value: Any) -> Decimal | None:
        if value in (None, ""):
            return None
        normalized = re.sub(r"[^\d.]", "", str(value))
        if not normalized:
            return None
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return None

    @staticmethod
    def _first(item: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in item:
                return item[key]
        return None
