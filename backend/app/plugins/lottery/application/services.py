import json
from math import ceil

from sqlalchemy.orm import Session

from app.core.config.settings import get_settings
from app.plugins.lottery.domain.constants import DLT_GAME_CODE
from app.plugins.lottery.domain.sync import DrawSyncCommand, DrawValidator
from app.plugins.lottery.infrastructure.persistence.models import LotteryDrawModel, LotterySyncRunModel
from app.plugins.lottery.infrastructure.persistence.repositories import LotteryRepository
from app.plugins.lottery.infrastructure.sources.sporttery import SportteryDrawSource
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

    def sync_draws(self, command: DrawSyncCommand) -> dict[str, object]:
        if self.repository.has_running_sync(DLT_GAME_CODE):
            raise AppError(
                code=ErrorCode.lottery_sync_already_running,
                message="A DLT sync run is already running.",
                status_code=409,
            )

        settings = get_settings()
        source = SportteryDrawSource(timeout_seconds=settings.lottery_dlt_sync_timeout_seconds)
        run = self.repository.create_sync_run(
            game_code=DLT_GAME_CODE,
            source=source.source,
            sync_type=command.sync_type,
            requested_page=command.page,
            requested_page_size=command.page_size,
            source_url=source.base_url,
        )
        self.repository.db.commit()

        fetched_count = inserted_count = updated_count = skipped_count = failed_count = 0
        latest_issue_no: str | None = None
        try:
            source_page = source.fetch_page(page=command.page, page_size=command.page_size)
            validator = DrawValidator()
            for record in source_page.records:
                fetched_count += 1
                validator.validate_dlt_record(record)
                action = self.repository.upsert_draw(record, force=command.force)
                if action == "inserted":
                    inserted_count += 1
                elif action == "updated":
                    updated_count += 1
                else:
                    skipped_count += 1
                latest_issue_no = max(latest_issue_no or record.issue_no, record.issue_no)

            status = "success" if failed_count == 0 else "partial_success"
            self.repository.finish_sync_run(
                run,
                status=status,
                fetched_count=fetched_count,
                inserted_count=inserted_count,
                updated_count=updated_count,
                skipped_count=skipped_count,
                failed_count=failed_count,
                latest_issue_no=latest_issue_no,
                raw_metadata=source_page.raw_metadata,
            )
            self.repository.db.commit()
            return self._serialize_sync_run(run)
        except AppError as exc:
            self.repository.db.rollback()
            run = self.repository.db.merge(run)
            self.repository.finish_sync_run(
                run,
                status="failed",
                fetched_count=fetched_count,
                inserted_count=inserted_count,
                updated_count=updated_count,
                skipped_count=skipped_count,
                failed_count=max(failed_count, 1),
                latest_issue_no=latest_issue_no,
                error_code=exc.code.value,
                error_message=exc.message,
            )
            self.repository.db.commit()
            return self._serialize_sync_run(run)
        except Exception as exc:
            self.repository.db.rollback()
            run = self.repository.db.merge(run)
            self.repository.finish_sync_run(
                run,
                status="failed",
                fetched_count=fetched_count,
                inserted_count=inserted_count,
                updated_count=updated_count,
                skipped_count=skipped_count,
                failed_count=max(failed_count, 1),
                latest_issue_no=latest_issue_no,
                error_code=ErrorCode.internal_error.value,
                error_message=str(exc),
            )
            self.repository.db.commit()
            raise

    def get_latest_sync_run(self) -> dict[str, object]:
        run = self.repository.get_latest_sync_run()
        if run is None:
            raise AppError(
                code=ErrorCode.lottery_sync_run_not_found,
                message="No lottery sync run is available yet.",
                status_code=404,
            )
        return self._serialize_sync_run(run)

    def list_sync_runs(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        sync_type: str | None = None,
    ) -> dict[str, object]:
        items, total = self.repository.list_sync_runs(
            page=page,
            page_size=page_size,
            status=status,
            sync_type=sync_type,
        )
        return {
            "items": [self._serialize_sync_run(item) for item in items],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": ceil(total / page_size) if total else 0,
            },
        }

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

    @staticmethod
    def _serialize_sync_run(run: LotterySyncRunModel) -> dict[str, object]:
        return {
            "run_id": run.id,
            "game_code": run.game_code,
            "source": run.source,
            "sync_type": run.sync_type,
            "status": run.status,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "duration_ms": run.duration_ms,
            "requested_page": run.requested_page,
            "requested_page_size": run.requested_page_size,
            "fetched_count": run.fetched_count,
            "inserted_count": run.inserted_count,
            "updated_count": run.updated_count,
            "skipped_count": run.skipped_count,
            "failed_count": run.failed_count,
            "latest_issue_no": run.latest_issue_no,
            "error_code": run.error_code,
            "error_message": run.error_message,
            "source_url": run.source_url,
        }
