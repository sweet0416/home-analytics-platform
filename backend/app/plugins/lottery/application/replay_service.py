import json
import random
from collections import Counter
from decimal import Decimal
from statistics import mean

from sqlalchemy.orm import Session

from app.plugins.lottery.application.services import LotteryService
from app.plugins.lottery.domain.constants import DLT_DISCLAIMER, DLT_GAME_CODE
from app.plugins.lottery.infrastructure.persistence.models import LotteryDrawModel
from app.plugins.lottery.infrastructure.persistence.repositories import LotteryRepository
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


class LotteryReplayService:
    def __init__(self, db: Session) -> None:
        self.repository = LotteryRepository(db)

    def get_replay_context(
        self,
        *,
        target_issue_no: str,
        sample_limit: int = 500,
    ) -> dict[str, object]:
        target_draw = self._get_target_draw(target_issue_no)
        training_draws = self.repository.list_draws_before_issue(
            target_issue_no,
            limit=sample_limit,
        )
        self._assert_no_future_data(target_issue_no=target_issue_no, draws=training_draws)
        serialized_training_draws = [
            LotteryService._serialize_draw(draw) for draw in training_draws
        ]
        issue_suffix = target_issue_no[-3:]
        same_period_draws = [
            draw
            for draw in serialized_training_draws
            if str(draw["issue_no"]).endswith(issue_suffix)
        ]
        cutoff_draw = training_draws[0] if training_draws else None
        warnings = self._build_sample_warnings(len(training_draws))
        return {
            "target": LotteryService._serialize_draw(target_draw),
            "cutoff": LotteryService._serialize_draw(cutoff_draw) if cutoff_draw else None,
            "sample_size": len(training_draws),
            "requested_sample_limit": sample_limit,
            "available_range": self._build_available_range(training_draws),
            "leakage_check": {
                "passed": True,
                "rule": "training issue_no must be smaller than target issue_no",
            },
            "warnings": warnings,
            "same_period_deviation": self._build_same_period_deviation(
                target=LotteryService._serialize_draw(target_draw),
                same_period_draws=same_period_draws,
            ),
        }

    def run_replay(
        self,
        *,
        target_issue_no: str,
        sets: int = 5,
        sample_limit: int = 500,
        same_period_count: int = 10,
        baseline_simulations: int = 10000,
        seed: int | None = None,
        same_period_weight: float = 45,
        frequency_weight: float = 25,
        missing_weight: float = 20,
        structure_weight: float = 10,
    ) -> dict[str, object]:
        target_draw = self._get_target_draw(target_issue_no)
        training_models = self.repository.list_draws_before_issue(
            target_issue_no,
            limit=sample_limit,
        )
        self._assert_no_future_data(target_issue_no=target_issue_no, draws=training_models)
        if not training_models:
            raise AppError(
                code=ErrorCode.lottery_draw_not_found,
                message="No past draw data is available before the target issue.",
                status_code=404,
            )

        training_draws = [LotteryService._serialize_draw(draw) for draw in training_models]
        target = LotteryService._serialize_draw(target_draw)
        cutoff_model = training_models[0]
        cutoff = training_draws[0]
        strategy_weights = LotteryService._normalize_recommendation_weights(
            same_period_weight=same_period_weight,
            frequency_weight=frequency_weight,
            missing_weight=missing_weight,
            structure_weight=structure_weight,
        )
        issue_suffix = target_issue_no[-3:]
        same_period_draws = [
            draw for draw in training_draws if str(draw["issue_no"]).endswith(issue_suffix)
        ][:same_period_count]
        same_period_deviation = self._build_same_period_deviation(
            target=target,
            same_period_draws=same_period_draws,
        )
        front_scores = LotteryService._score_recommendation_numbers(
            area="front",
            min_number=1,
            max_number=35,
            recent_draws=training_draws,
            same_period_draws=same_period_draws,
            strategy_weights=strategy_weights,
        )
        back_scores = LotteryService._score_recommendation_numbers(
            area="back",
            min_number=1,
            max_number=12,
            recent_draws=training_draws,
            same_period_draws=same_period_draws,
            strategy_weights=strategy_weights,
        )
        generated_sets = LotteryService._build_recommendation_sets(
            front_scores=front_scores,
            back_scores=back_scores,
            recent_draws=training_draws,
            structure_weight=float(strategy_weights["structure"]),
            limit=sets,
        )
        baseline = self._build_random_baseline(
            target_front_numbers=list(target["front_numbers"]),
            target_back_numbers=list(target["back_numbers"]),
            simulations=baseline_simulations,
            seed=seed,
        )
        evaluated_sets = [
            self._evaluate_generated_set(
                generated_set=item,
                target=target,
                baseline_scores=list(baseline["scores"]),
            )
            for item in generated_sets
        ]
        warnings = self._build_sample_warnings(len(training_draws))
        if len(same_period_draws) < same_period_count:
            warnings.append(
                {
                    "code": "SAME_PERIOD_SAMPLE_LIMITED",
                    "message": "Same-period historical sample is smaller than requested.",
                }
            )
        strategy_params = {
            "sets": sets,
            "sample_limit": sample_limit,
            "same_period_count": same_period_count,
            "baseline_simulations": baseline_simulations,
            "seed": seed,
            "weights": strategy_weights,
        }
        result_summary = self._build_result_summary(evaluated_sets, baseline)
        replay_run = self.repository.create_replay_run(
            game_code=DLT_GAME_CODE,
            target_issue_no=target_issue_no,
            target_draw_date=target_draw.draw_date,
            cutoff_issue_no=cutoff_model.issue_no,
            cutoff_draw_date=cutoff_model.draw_date,
            strategy_name="same_period_frequency_missing_structure",
            strategy_params_json=json.dumps(strategy_params, ensure_ascii=False),
            sample_size=len(training_draws),
            baseline_simulations=baseline_simulations,
            status="success",
            warnings_json=json.dumps(warnings, ensure_ascii=False),
            result_summary_json=json.dumps(result_summary, ensure_ascii=False),
        )
        for item in evaluated_sets:
            self.repository.add_replay_generated_set(
                replay_run=replay_run,
                rank=int(item["rank"]),
                front_numbers_json=json.dumps(item["front_numbers"], ensure_ascii=False),
                back_numbers_json=json.dumps(item["back_numbers"], ensure_ascii=False),
                score=Decimal(str(item["score"])),
                rationale_json=json.dumps(item["rationale"], ensure_ascii=False),
                front_match_count=int(item["front_match_count"]),
                back_match_count=int(item["back_match_count"]),
                prize_tier=item["prize_tier"],
                baseline_percentile=Decimal(str(item["baseline_percentile"])),
            )
        self.repository.db.commit()

        return {
            "run_id": replay_run.id,
            "target_issue_no": target_issue_no,
            "target_draw": target,
            "cutoff_issue_no": cutoff["issue_no"],
            "cutoff_draw_date": cutoff["draw_date"],
            "sample_size": len(training_draws),
            "same_period_count": len(same_period_draws),
            "strategy_name": replay_run.strategy_name,
            "strategy_params": strategy_params,
            "generated_sets": evaluated_sets,
            "baseline": {key: value for key, value in baseline.items() if key != "scores"},
            "warnings": warnings,
            "leakage_check": {
                "passed": True,
                "rule": "training issue_no must be smaller than target issue_no",
            },
            "same_period_deviation": same_period_deviation,
            "disclaimer": DLT_DISCLAIMER,
        }

    def _get_target_draw(self, target_issue_no: str) -> LotteryDrawModel:
        target_draw = self.repository.get_draw_by_issue(target_issue_no.strip())
        if target_draw is None:
            raise AppError(
                code=ErrorCode.lottery_draw_not_found,
                message=f"Target lottery draw '{target_issue_no}' was not found.",
                status_code=404,
            )
        return target_draw

    @staticmethod
    def _assert_no_future_data(
        *,
        target_issue_no: str,
        draws: list[LotteryDrawModel],
    ) -> None:
        leaked = [draw.issue_no for draw in draws if draw.issue_no >= target_issue_no]
        if leaked:
            raise AppError(
                code=ErrorCode.validation_error,
                message=f"Replay training data contains future issues: {', '.join(leaked[:5])}",
                status_code=422,
            )

    @staticmethod
    def _build_sample_warnings(sample_size: int) -> list[dict[str, str]]:
        warnings: list[dict[str, str]] = []
        if sample_size < 50:
            warnings.append(
                {
                    "code": "SAMPLE_TOO_SMALL",
                    "message": "Sample size is too small for stable statistical comparison.",
                }
            )
        elif sample_size < 200:
            warnings.append(
                {
                    "code": "SAMPLE_LIMITED",
                    "message": "Sample size is usable but still limited; avoid over-interpreting.",
                }
            )
        return warnings

    @staticmethod
    def _build_available_range(draws: list[LotteryDrawModel]) -> dict[str, object]:
        if not draws:
            return {
                "earliest_issue_no": None,
                "latest_issue_no": None,
                "earliest_draw_date": None,
                "latest_draw_date": None,
            }
        chronological = list(reversed(draws))
        return {
            "earliest_issue_no": chronological[0].issue_no,
            "latest_issue_no": draws[0].issue_no,
            "earliest_draw_date": chronological[0].draw_date.isoformat(),
            "latest_draw_date": draws[0].draw_date.isoformat(),
        }

    @staticmethod
    def _build_random_baseline(
        *,
        target_front_numbers: list[int],
        target_back_numbers: list[int],
        simulations: int,
        seed: int | None,
    ) -> dict[str, object]:
        rng = random.Random(seed)
        target_front = set(target_front_numbers)
        target_back = set(target_back_numbers)
        scores: list[int] = []
        front_matches: list[int] = []
        back_matches: list[int] = []
        any_prize_count = 0
        for _ in range(simulations):
            front = set(rng.sample(range(1, 36), 5))
            back = set(rng.sample(range(1, 13), 2))
            front_count = len(front & target_front)
            back_count = len(back & target_back)
            score = front_count * 10 + back_count
            scores.append(score)
            front_matches.append(front_count)
            back_matches.append(back_count)
            if LotteryReplayService._resolve_prize_tier(front_count, back_count) is not None:
                any_prize_count += 1

        return {
            "simulations": simulations,
            "seed": seed,
            "average_front_match": round(mean(front_matches), 4),
            "average_back_match": round(mean(back_matches), 4),
            "average_score": round(mean(scores), 4),
            "any_prize_rate": round(any_prize_count / simulations, 6),
            "scores": scores,
            "explanation": "Random baseline samples 5 front and 2 back numbers uniformly.",
        }

    @staticmethod
    def _build_same_period_deviation(
        *,
        target: dict[str, object],
        same_period_draws: list[dict[str, object]],
    ) -> dict[str, object]:
        target_front = list(target["front_numbers"])
        target_back = list(target["back_numbers"])
        target_metrics = LotteryService._build_draw_metrics(
            issue_no=str(target["issue_no"]),
            front_numbers=target_front,
            back_numbers=target_back,
        )
        historical_metrics = [
            LotteryService._build_draw_metrics(
                issue_no=str(draw["issue_no"]),
                front_numbers=list(draw["front_numbers"]),
                back_numbers=list(draw["back_numbers"]),
            )
            for draw in same_period_draws
        ]
        sample_size = len(same_period_draws)
        front_repeat_values = [
            len(set(target_front) & set(draw["front_numbers"]))
            for draw in same_period_draws
        ]
        back_repeat_values = [
            len(set(target_back) & set(draw["back_numbers"]))
            for draw in same_period_draws
        ]
        notes = [
            "所有历史同期样本都早于目标期，不包含目标期或之后的数据。",
            "偏离度描述的是历史样本距离，不代表下一期概率变化。",
        ]
        if sample_size < 5:
            notes.append(
                "历史同期样本较少，请把偏离度当作粗略观察，不要过度解读。"
            )

        return {
            "issue_suffix": str(target["issue_no"])[-3:],
            "sample_size": sample_size,
            "front_repeat": LotteryReplayService._build_numeric_deviation_metric(
                label="front repeat",
                target_value=round(mean(front_repeat_values), 2)
                if front_repeat_values
                else 0,
                historical_average=round(5 * 5 / 35, 2),
                high_threshold=1.0,
                medium_threshold=0.5,
                sample_size=sample_size,
            ),
            "back_repeat": LotteryReplayService._build_numeric_deviation_metric(
                label="back repeat",
                target_value=round(mean(back_repeat_values), 2)
                if back_repeat_values
                else 0,
                historical_average=round(2 * 2 / 12, 2),
                high_threshold=0.8,
                medium_threshold=0.35,
                sample_size=sample_size,
            ),
            "front_sum": LotteryReplayService._build_numeric_deviation_metric(
                label="front sum",
                target_value=int(target_metrics["front_sum"]),
                historical_average=LotteryReplayService._metric_average(
                    historical_metrics,
                    "front_sum",
                ),
                high_threshold=25,
                medium_threshold=12,
                sample_size=sample_size,
            ),
            "front_span": LotteryReplayService._build_numeric_deviation_metric(
                label="front span",
                target_value=int(target_metrics["front_span"]),
                historical_average=LotteryReplayService._metric_average(
                    historical_metrics,
                    "front_span",
                ),
                high_threshold=10,
                medium_threshold=5,
                sample_size=sample_size,
            ),
            "front_zone": LotteryReplayService._build_pattern_deviation_metric(
                target_pattern=str(target_metrics["front_zone_pattern"]),
                historical_patterns=[
                    str(item["front_zone_pattern"]) for item in historical_metrics
                ],
                sample_size=sample_size,
            ),
            "front_route012": LotteryReplayService._build_pattern_deviation_metric(
                target_pattern=str(target_metrics["front_route012_pattern"]),
                historical_patterns=[
                    str(item["front_route012_pattern"]) for item in historical_metrics
                ],
                sample_size=sample_size,
            ),
            "notes": notes,
        }

    @staticmethod
    def _metric_average(
        metrics: list[dict[str, object]],
        key: str,
    ) -> float:
        values = [float(item[key]) for item in metrics if item.get(key) is not None]
        return round(mean(values), 2) if values else 0

    @staticmethod
    def _build_numeric_deviation_metric(
        *,
        label: str,
        target_value: float,
        historical_average: float,
        high_threshold: float,
        medium_threshold: float,
        sample_size: int,
    ) -> dict[str, object]:
        deviation = round(target_value - historical_average, 2)
        absolute_deviation = abs(deviation)
        if sample_size < 3:
            level = "sample_limited"
        elif absolute_deviation >= high_threshold:
            level = "high"
        elif absolute_deviation >= medium_threshold:
            level = "medium"
        else:
            level = "low"
        return {
            "label": label,
            "target_value": target_value,
            "historical_average": historical_average,
            "deviation": deviation,
            "level": level,
        }

    @staticmethod
    def _build_pattern_deviation_metric(
        *,
        target_pattern: str,
        historical_patterns: list[str],
        sample_size: int,
    ) -> dict[str, object]:
        pattern_counter = Counter(historical_patterns)
        top_pattern, top_count = (
            pattern_counter.most_common(1)[0] if pattern_counter else ("--", 0)
        )
        target_count = pattern_counter.get(target_pattern, 0)
        target_rate = round(target_count / sample_size, 4) if sample_size else 0
        if sample_size < 3:
            level = "sample_limited"
        elif target_rate >= 0.2:
            level = "common"
        elif target_rate > 0:
            level = "uncommon"
        else:
            level = "not_seen"
        return {
            "target_pattern": target_pattern,
            "historical_top_pattern": top_pattern,
            "historical_top_rate": round(top_count / sample_size, 4) if sample_size else 0,
            "target_pattern_rate": target_rate,
            "level": level,
        }

    @staticmethod
    def _evaluate_generated_set(
        *,
        generated_set: dict[str, object],
        target: dict[str, object],
        baseline_scores: list[int],
    ) -> dict[str, object]:
        front_numbers = list(generated_set["front_numbers"])
        back_numbers = list(generated_set["back_numbers"])
        front_match_count = len(set(front_numbers) & set(target["front_numbers"]))
        back_match_count = len(set(back_numbers) & set(target["back_numbers"]))
        match_score = front_match_count * 10 + back_match_count
        baseline_percentile = (
            sum(1 for score in baseline_scores if score <= match_score) / len(baseline_scores)
            if baseline_scores
            else 0
        )
        return {
            **generated_set,
            "front_matches": sorted(set(front_numbers) & set(target["front_numbers"])),
            "back_matches": sorted(set(back_numbers) & set(target["back_numbers"])),
            "front_match_count": front_match_count,
            "back_match_count": back_match_count,
            "match_key": f"{front_match_count}+{back_match_count}",
            "prize_tier": LotteryReplayService._resolve_prize_tier(
                front_match_count,
                back_match_count,
            ),
            "baseline_percentile": round(baseline_percentile, 4),
        }

    @staticmethod
    def _resolve_prize_tier(front_match_count: int, back_match_count: int) -> int | None:
        prize_rules = {
            (5, 2): 1,
            (5, 1): 2,
            (5, 0): 3,
            (4, 2): 3,
            (4, 1): 4,
            (4, 0): 5,
            (3, 2): 5,
            (3, 1): 6,
            (2, 2): 6,
            (3, 0): 7,
            (2, 1): 7,
            (1, 2): 7,
            (0, 2): 7,
        }
        return prize_rules.get((front_match_count, back_match_count))

    @staticmethod
    def _build_result_summary(
        generated_sets: list[dict[str, object]],
        baseline: dict[str, object],
    ) -> dict[str, object]:
        best_set = max(
            generated_sets,
            key=lambda item: (
                int(item["front_match_count"]),
                int(item["back_match_count"]),
                float(item["baseline_percentile"]),
            ),
            default=None,
        )
        return {
            "generated_count": len(generated_sets),
            "best_match_key": best_set["match_key"] if best_set else None,
            "best_baseline_percentile": best_set["baseline_percentile"] if best_set else None,
            "baseline_average_score": baseline["average_score"],
        }
