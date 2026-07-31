import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class TargetFundLink:
    parent_fund_code: str
    target_fund_code: str
    target_fund_name: str
    target_allocation_ratio: Decimal
    report_date: date
    source_url: str


def parse_target_fund_links(raw_value: str) -> list[TargetFundLink]:
    if not raw_value.strip():
        return []
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError("Fund target links must be valid JSON.") from exc
    if not isinstance(payload, list):
        raise ValueError("Fund target links must be a JSON array.")

    links: list[TargetFundLink] = []
    parent_codes: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Each fund target link must be an object.")
        parent_code = str(item.get("parent_fund_code", "")).strip()
        target_code = str(item.get("target_fund_code", "")).strip()
        target_name = str(item.get("target_fund_name", "")).strip()
        source_url = str(item.get("source_url", "")).strip()
        if not all((parent_code, target_code, target_name, source_url)):
            raise ValueError("Fund target link fields cannot be empty.")
        if parent_code in parent_codes:
            raise ValueError(f"Duplicate target link for fund {parent_code}.")
        try:
            ratio = Decimal(str(item.get("target_allocation_ratio", "")))
            report_date = date.fromisoformat(str(item.get("report_date", "")))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(
                f"Invalid ratio or report date for fund {parent_code}."
            ) from exc
        if ratio <= 0 or ratio > 1:
            raise ValueError(
                f"Target allocation ratio for fund {parent_code} must be in (0, 1]."
            )
        links.append(
            TargetFundLink(
                parent_fund_code=parent_code,
                target_fund_code=target_code,
                target_fund_name=target_name,
                target_allocation_ratio=ratio,
                report_date=report_date,
                source_url=source_url,
            )
        )
        parent_codes.add(parent_code)
    return links
