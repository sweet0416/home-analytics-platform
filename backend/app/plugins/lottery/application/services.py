import json
from math import ceil

from sqlalchemy.orm import Session

from app.plugins.lottery.infrastructure.persistence.models import LotteryDrawModel
from app.plugins.lottery.infrastructure.persistence.repositories import LotteryRepository
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


class LotteryService:
    def __init__(self, db: Session) -> None:
        self.repository = LotteryRepository(db)

    def get_current_rule(self) -> dict[str, object]:
        rule = self.repository.get_current_rule()
        if rule is None:
            raise AppError(
                code=ErrorCode.lottery_rule_not_found,
                message="Current lottery rule was not found.",
                status_code=404,
            )
        return {
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "game_code": rule.game_code,
            "front": {
                "count": rule.front_count,
                "min": rule.front_min,
                "max": rule.front_max,
            },
            "back": {
                "count": rule.back_count,
                "min": rule.back_min,
                "max": rule.back_max,
            },
            "base_price": str(rule.base_price),
            "addon_price": str(rule.addon_price),
            "addon_supported": rule.addon_supported,
            "official_url": rule.official_url,
            "prize_tiers": [
                {
                    "tier": tier.tier,
                    "tier_name": tier.tier_name,
                    "front_match_count": tier.front_match_count,
                    "back_match_count": tier.back_match_count,
                    "is_floating": tier.is_floating,
                    "base_prize_amount": (
                        str(tier.base_prize_amount) if tier.base_prize_amount is not None else None
                    ),
                    "addon_multiplier": (
                        str(tier.addon_multiplier) if tier.addon_multiplier is not None else None
                    ),
                    "description": tier.description,
                }
                for tier in sorted(rule.prize_tiers, key=lambda item: item.sort_order)
            ],
        }

    def list_draws(self, page: int, page_size: int) -> dict[str, object]:
        items, total = self.repository.list_draws(page=page, page_size=page_size)
        return {
            "items": [self._serialize_draw(item) for item in items],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": ceil(total / page_size) if total else 0,
            },
        }

    def get_latest_draw(self) -> dict[str, object]:
        draw = self.repository.get_latest_draw()
        if draw is None:
            raise AppError(
                code=ErrorCode.lottery_draw_not_found,
                message="No lottery draw data is available yet.",
                status_code=404,
            )
        return self._serialize_draw(draw)

    def get_draw_by_issue(self, issue_no: str) -> dict[str, object]:
        draw = self.repository.get_draw_by_issue(issue_no)
        if draw is None:
            raise AppError(
                code=ErrorCode.lottery_draw_not_found,
                message=f"Lottery draw '{issue_no}' was not found.",
                status_code=404,
            )
        return self._serialize_draw(draw)

    @staticmethod
    def _serialize_draw(draw: LotteryDrawModel) -> dict[str, object]:
        return {
            "issue_no": draw.issue_no,
            "draw_date": draw.draw_date.isoformat(),
            "front_numbers": json.loads(draw.front_numbers_json),
            "back_numbers": json.loads(draw.back_numbers_json),
            "sales_amount": str(draw.sales_amount) if draw.sales_amount is not None else None,
            "pool_amount": str(draw.pool_amount) if draw.pool_amount is not None else None,
            "source_url": draw.source_url,
        }

