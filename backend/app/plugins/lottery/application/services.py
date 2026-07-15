import json
from dataclasses import replace
from math import ceil
from statistics import mean

from loguru import logger
from sqlalchemy.orm import Session

from app.core.config.settings import Settings, get_settings
from app.plugins.lottery.domain.constants import DLT_GAME_CODE
from app.plugins.lottery.domain.sync import (
    DrawSource,
    DrawSourcePage,
    DrawSyncCommand,
    DrawValidator,
)
from app.plugins.lottery.infrastructure.persistence.models import (
    LotteryDrawModel,
    LotterySyncRunModel,
)
from app.plugins.lottery.infrastructure.persistence.repositories import LotteryRepository
from app.plugins.lottery.infrastructure.sources.five_hundred import FiveHundredDrawSource
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

    def get_basic_statistics(self, limit: int = 100) -> dict[str, object]:
        draws = self.repository.list_recent_draws(limit=limit)
        serialized_draws = [self._serialize_draw(draw) for draw in draws]
        front_rows = [item["front_numbers"] for item in serialized_draws]
        back_rows = [item["back_numbers"] for item in serialized_draws]
        issue_numbers = [str(item["issue_no"]) for item in serialized_draws]

        front_frequency = self._build_frequency(
            rows=front_rows,
            min_number=1,
            max_number=35,
            recent_issue_numbers=issue_numbers,
        )
        back_frequency = self._build_frequency(
            rows=back_rows,
            min_number=1,
            max_number=12,
            recent_issue_numbers=issue_numbers,
        )
        per_draw = [
            self._build_draw_metrics(
                issue_no=str(item["issue_no"]),
                front_numbers=list(item["front_numbers"]),
                back_numbers=list(item["back_numbers"]),
            )
            for item in serialized_draws
        ]

        return {
            "sample_size": len(serialized_draws),
            "requested_limit": limit,
            "latest_issue_no": issue_numbers[0] if issue_numbers else None,
            "front_frequency": front_frequency,
            "back_frequency": back_frequency,
            "hot_numbers": {
                "front": sorted(
                    front_frequency,
                    key=lambda item: (-item["count"], item["number"]),
                )[:10],
                "back": sorted(
                    back_frequency,
                    key=lambda item: (-item["count"], item["number"]),
                )[:6],
            },
            "cold_numbers": {
                "front": sorted(
                    front_frequency,
                    key=lambda item: (item["count"], item["number"]),
                )[:10],
                "back": sorted(
                    back_frequency,
                    key=lambda item: (item["count"], item["number"]),
                )[:6],
            },
            "sum": self._summarize_numeric([int(item["front_sum"]) for item in per_draw]),
            "span": self._summarize_numeric([int(item["front_span"]) for item in per_draw]),
            "parity": self._summarize_distribution(
                [str(item["front_parity_pattern"]) for item in per_draw]
            ),
            "size": self._summarize_distribution(
                [str(item["front_size_pattern"]) for item in per_draw]
            ),
            "zone": self._summarize_distribution(
                [str(item["front_zone_pattern"]) for item in per_draw]
            ),
            "route012": self._summarize_distribution(
                [str(item["front_route012_pattern"]) for item in per_draw]
            ),
            "recent_metrics": per_draw[:20],
            "trend": list(reversed(per_draw)),
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
        sources = self._build_dlt_sources(settings)
        run = self.repository.create_sync_run(
            game_code=DLT_GAME_CODE,
            source="automatic",
            sync_type=command.sync_type,
            requested_page=command.page,
            requested_page_size=command.page_size,
            source_url=sources[0].base_url,
        )
        self.repository.db.commit()

        fetched_count = inserted_count = updated_count = skipped_count = failed_count = 0
        latest_issue_no: str | None = None
        try:
            source_page = self._fetch_source_page(
                sources=sources,
                page=command.page,
                page_size=command.page_size,
            )
            for record in source_page.records:
                fetched_count += 1
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
                source=source_page.source,
                source_url=source_page.source_url,
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

    @staticmethod
    def _build_dlt_sources(settings: Settings) -> list[DrawSource]:
        sources: list[DrawSource] = [
            SportteryDrawSource(
                timeout_seconds=settings.lottery_dlt_sync_timeout_seconds,
                base_url=settings.lottery_dlt_sporttery_url,
            )
        ]
        if settings.lottery_dlt_fallback_enabled:
            sources.append(
                FiveHundredDrawSource(
                    timeout_seconds=settings.lottery_dlt_sync_timeout_seconds,
                    base_url=settings.lottery_dlt_500_history_url,
                )
            )
        return sources

    @staticmethod
    def _fetch_source_page(
        *,
        sources: list[DrawSource],
        page: int,
        page_size: int,
    ) -> DrawSourcePage:
        attempts: list[dict[str, object]] = []
        validator = DrawValidator()
        for source in sources:
            try:
                source_page = source.fetch_page(page=page, page_size=page_size)
                for record in source_page.records:
                    validator.validate_dlt_record(record)
                attempts.append({"source": source.source, "status": "success"})
                logger.info(
                    "DLT sync selected source={} records={}",
                    source.source,
                    len(source_page.records),
                )
                metadata = dict(source_page.raw_metadata)
                metadata["source_attempts"] = attempts
                return replace(source_page, raw_metadata=metadata)
            except AppError as exc:
                attempts.append(
                    {
                        "source": source.source,
                        "status": "failed",
                        "error_code": exc.code.value,
                        "error_message": exc.message,
                    }
                )
                logger.warning(
                    "DLT sync source failed source={} code={} message={}",
                    source.source,
                    exc.code.value,
                    exc.message,
                )

        failure_summary = "; ".join(
            f"{attempt['source']}: {attempt['error_message']}" for attempt in attempts
        )
        raise AppError(
            code=ErrorCode.lottery_sync_source_unavailable,
            message=f"All configured DLT sources failed. {failure_summary}",
            status_code=502,
        )

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
    def _build_frequency(
        *,
        rows: list[list[int]],
        min_number: int,
        max_number: int,
        recent_issue_numbers: list[str],
    ) -> list[dict[str, object]]:
        counts = {number: 0 for number in range(min_number, max_number + 1)}
        last_seen_issue: dict[int, str | None] = {
            number: None for number in range(min_number, max_number + 1)
        }
        missing = {number: len(rows) for number in range(min_number, max_number + 1)}

        for index, numbers in enumerate(rows):
            issue_no = recent_issue_numbers[index]
            for number in numbers:
                counts[number] += 1
                if last_seen_issue[number] is None:
                    last_seen_issue[number] = issue_no
                    missing[number] = index

        return [
            {
                "number": number,
                "count": counts[number],
                "missing": missing[number],
                "last_seen_issue_no": last_seen_issue[number],
            }
            for number in range(min_number, max_number + 1)
        ]

    @staticmethod
    def _build_draw_metrics(
        *,
        issue_no: str,
        front_numbers: list[int],
        back_numbers: list[int],
    ) -> dict[str, object]:
        front_sum = sum(front_numbers)
        front_span = max(front_numbers) - min(front_numbers)
        odd_count = sum(1 for number in front_numbers if number % 2 == 1)
        big_count = sum(1 for number in front_numbers if number >= 18)
        zone_counts = [
            sum(1 for number in front_numbers if 1 <= number <= 12),
            sum(1 for number in front_numbers if 13 <= number <= 24),
            sum(1 for number in front_numbers if 25 <= number <= 35),
        ]
        route_counts = [
            sum(1 for number in front_numbers if number % 3 == residue)
            for residue in (0, 1, 2)
        ]
        return {
            "issue_no": issue_no,
            "front_sum": front_sum,
            "front_span": front_span,
            "front_parity_pattern": f"{odd_count}:{len(front_numbers) - odd_count}",
            "front_size_pattern": f"{big_count}:{len(front_numbers) - big_count}",
            "front_zone_pattern": ":".join(str(count) for count in zone_counts),
            "front_route012_pattern": ":".join(str(count) for count in route_counts),
            "front_zone_counts": zone_counts,
            "front_route012_counts": route_counts,
            "back_sum": sum(back_numbers),
        }

    @staticmethod
    def _summarize_numeric(values: list[int]) -> dict[str, object]:
        if not values:
            return {"min": None, "max": None, "average": None}
        return {
            "min": min(values),
            "max": max(values),
            "average": round(mean(values), 2),
        }

    @staticmethod
    def _summarize_distribution(values: list[str]) -> list[dict[str, object]]:
        counts: dict[str, int] = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        return [
            {"pattern": pattern, "count": count}
            for pattern, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]

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
