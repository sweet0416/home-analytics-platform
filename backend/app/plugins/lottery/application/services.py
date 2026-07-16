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

    def get_draw_coverage(self) -> dict[str, object]:
        latest_draw = self.repository.get_latest_draw()
        earliest_draw = self.repository.get_earliest_draw()
        total = self.repository.count_draws()
        if latest_draw is None or earliest_draw is None:
            return {
                "total": 0,
                "latest_issue_no": None,
                "latest_draw_date": None,
                "earliest_issue_no": None,
                "earliest_draw_date": None,
                "start_year": None,
                "end_year": None,
                "year_span": 0,
                "status": "empty",
                "status_label": "暂无数据",
                "description": "还没有入库的开奖数据，先执行同步或历史回填。",
            }

        start_year = earliest_draw.draw_date.year
        end_year = latest_draw.draw_date.year
        year_span = end_year - start_year + 1
        if total >= 1500:
            status = "good"
            status_label = "长期分析可用"
            description = "历史数据覆盖较长，适合做趋势、遗漏、冷热和历史同期分析。"
        elif total >= 500:
            status = "usable"
            status_label = "基础分析可用"
            description = "数据量足够做基础统计，继续回填可提升长期分析稳定性。"
        else:
            status = "limited"
            status_label = "样本偏少"
            description = "当前数据较少，建议先补齐更多历史开奖。"

        return {
            "total": total,
            "latest_issue_no": latest_draw.issue_no,
            "latest_draw_date": latest_draw.draw_date.isoformat(),
            "earliest_issue_no": earliest_draw.issue_no,
            "earliest_draw_date": earliest_draw.draw_date.isoformat(),
            "start_year": start_year,
            "end_year": end_year,
            "year_span": year_span,
            "status": status,
            "status_label": status_label,
            "description": description,
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

    def get_omission_statistics(self, limit: int = 100) -> dict[str, object]:
        draws = [
            self._serialize_draw(draw)
            for draw in self.repository.list_recent_draws(limit=limit)
        ]
        front_items = self._build_omission_items(
            draws=draws,
            area="front",
            min_number=1,
            max_number=35,
        )
        back_items = self._build_omission_items(
            draws=draws,
            area="back",
            min_number=1,
            max_number=12,
        )

        return {
            "sample_size": len(draws),
            "requested_limit": limit,
            "latest_issue_no": str(draws[0]["issue_no"]) if draws else None,
            "front": front_items,
            "back": back_items,
        }

    def get_number_omission_detail(
        self,
        *,
        area: str,
        number: int,
        limit: int = 200,
    ) -> dict[str, object]:
        if area not in {"front", "back"}:
            raise AppError(
                code=ErrorCode.validation_error,
                message="Lottery number area must be either 'front' or 'back'.",
                status_code=422,
            )
        max_number = 35 if area == "front" else 12
        if number < 1 or number > max_number:
            raise AppError(
                code=ErrorCode.validation_error,
                message=f"Lottery {area} number must be between 1 and {max_number}.",
                status_code=422,
            )

        draws = [
            self._serialize_draw(draw)
            for draw in self.repository.list_recent_draws(limit=limit)
        ]
        item = self._build_omission_item(draws=draws, area=area, number=number)
        hit_issues = [
            {
                "issue_no": str(draw["issue_no"]),
                "draw_date": str(draw["draw_date"]),
            }
            for draw in draws
            if number in draw[f"{area}_numbers"]
        ]

        return {
            **item,
            "sample_size": len(draws),
            "requested_limit": limit,
            "hit_issues": hit_issues,
        }

    def get_same_period_analysis(
        self,
        *,
        issue_no: str | None = None,
        count: int = 5,
    ) -> dict[str, object]:
        normalized_issue_no = issue_no.strip() if issue_no is not None else None
        target_draw = self._resolve_same_period_target(normalized_issue_no)
        if target_draw is None:
            raise AppError(
                code=ErrorCode.lottery_draw_not_found,
                message="Target lottery draw was not found.",
                status_code=404,
            )

        target = self._serialize_draw(target_draw)
        target_issue_no = str(target["issue_no"])
        if len(target_issue_no) < 3:
            raise AppError(
                code=ErrorCode.validation_error,
                message="Target lottery issue number is too short for same-period analysis.",
                status_code=422,
            )

        issue_suffix = target_issue_no[-3:]
        historical_draws = [
            self._serialize_draw(draw)
            for draw in self.repository.list_draws_by_issue_suffix(
                issue_suffix=issue_suffix,
                exclude_issue_no=target_issue_no,
                limit=count,
            )
        ]
        target_front_numbers = set(target["front_numbers"])
        target_back_numbers = set(target["back_numbers"])

        return {
            "target": target,
            "issue_suffix": issue_suffix,
            "requested_count": count,
            "items": [
                {
                    "draw": draw,
                    "front_matches": sorted(target_front_numbers & set(draw["front_numbers"])),
                    "back_matches": sorted(target_back_numbers & set(draw["back_numbers"])),
                    "front_match_count": len(target_front_numbers & set(draw["front_numbers"])),
                    "back_match_count": len(target_back_numbers & set(draw["back_numbers"])),
                }
                for draw in historical_draws
            ],
        }

    def _resolve_same_period_target(
        self,
        issue_no: str | None,
    ) -> LotteryDrawModel | None:
        if issue_no is None:
            return self.repository.get_latest_draw()
        if len(issue_no) == 3 and issue_no.isdigit():
            return self.repository.get_latest_draw_by_issue_suffix(issue_suffix=issue_no)
        return self.repository.get_draw_by_issue(issue_no)

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

    def backfill_draws(
        self,
        *,
        start_page: int = 1,
        page_count: int = 3,
        page_size: int = 100,
        force: bool = False,
    ) -> dict[str, object]:
        runs: list[dict[str, object]] = []
        totals = {
            "fetched_count": 0,
            "inserted_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
        }

        for page in range(start_page, start_page + page_count):
            run = self.sync_draws(
                DrawSyncCommand(
                    sync_type="backfill",
                    page=page,
                    page_size=page_size,
                    force=force,
                )
            )
            runs.append(run)
            for key in totals:
                totals[key] += int(run[key])
            if run["status"] == "failed":
                break

        statuses = {str(run["status"]) for run in runs}
        if not runs:
            status = "failed"
        elif statuses == {"success"}:
            status = "success"
        elif "failed" in statuses:
            status = "partial_success" if len(runs) > 1 else "failed"
        else:
            status = "partial_success"

        latest_issue_numbers = [
            str(run["latest_issue_no"])
            for run in runs
            if run["latest_issue_no"] is not None
        ]

        return {
            "status": status,
            "start_page": start_page,
            "page_count": page_count,
            "page_size": page_size,
            "executed_pages": len(runs),
            "latest_issue_no": max(latest_issue_numbers) if latest_issue_numbers else None,
            "runs": runs,
            **totals,
        }

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

    @classmethod
    def _build_omission_items(
        cls,
        *,
        draws: list[dict[str, object]],
        area: str,
        min_number: int,
        max_number: int,
    ) -> list[dict[str, object]]:
        return [
            cls._build_omission_item(draws=draws, area=area, number=number)
            for number in range(min_number, max_number + 1)
        ]

    @staticmethod
    def _build_omission_item(
        *,
        draws: list[dict[str, object]],
        area: str,
        number: int,
    ) -> dict[str, object]:
        chronological_draws = list(reversed(draws))
        current_missing = 0
        appearances = 0
        last_seen_issue_no: str | None = None
        last_seen_date: str | None = None
        completed_gaps: list[int] = []
        running_gap = 0
        trend: list[dict[str, object]] = []

        for draw in chronological_draws:
            issue_no = str(draw["issue_no"])
            draw_date = str(draw["draw_date"])
            numbers = draw[f"{area}_numbers"]
            is_hit = number in numbers
            if is_hit:
                appearances += 1
                completed_gaps.append(running_gap)
                running_gap = 0
                current_missing = 0
                last_seen_issue_no = issue_no
                last_seen_date = draw_date
            else:
                running_gap += 1
                current_missing += 1

            trend.append(
                {
                    "issue_no": issue_no,
                    "draw_date": draw_date,
                    "is_hit": is_hit,
                    "missing": current_missing,
                }
            )

        gaps = [*completed_gaps, running_gap] if chronological_draws else []
        max_missing = max((int(item["missing"]) for item in trend), default=0)
        average_missing = round(mean(gaps), 2) if gaps else 0

        return {
            "area": area,
            "number": number,
            "appearances": appearances,
            "current_missing": current_missing,
            "max_missing": max_missing,
            "average_missing": average_missing,
            "last_seen_issue_no": last_seen_issue_no,
            "last_seen_date": last_seen_date,
            "trend": trend,
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
