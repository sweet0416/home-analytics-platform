import json
import random
from collections import Counter
from dataclasses import replace
from itertools import combinations
from math import ceil, comb, erf, log2, sqrt
from statistics import mean

from loguru import logger
from sqlalchemy.orm import Session

from app.core.config.settings import Settings, get_settings
from app.plugins.lottery.domain.constants import DLT_DISCLAIMER, DLT_GAME_CODE
from app.plugins.lottery.domain.sync import (
    DrawSource,
    DrawSourcePage,
    DrawSyncCommand,
    DrawValidator,
)
from app.plugins.lottery.infrastructure.persistence.models import (
    LotteryDrawModel,
    LotterySavedCombinationModel,
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

    def list_saved_combinations(self) -> list[dict[str, object]]:
        return [
            self._serialize_saved_combination(item)
            for item in self.repository.list_saved_combinations()
        ]

    def save_combination(
        self,
        *,
        label: str,
        source: str,
        front_numbers: list[int],
        back_numbers: list[int],
        favorite: bool,
        note: str,
    ) -> dict[str, object]:
        combination = self.repository.save_combination(
            label=label.strip(),
            source=source.strip(),
            front_numbers_json=json.dumps(sorted(front_numbers), ensure_ascii=False),
            back_numbers_json=json.dumps(sorted(back_numbers), ensure_ascii=False),
            favorite=favorite,
            note=note.strip(),
        )
        self.repository.db.commit()
        self.repository.db.refresh(combination)
        return self._serialize_saved_combination(combination)

    def update_saved_combination(
        self,
        combination_id: int,
        *,
        label: str | None = None,
        source: str | None = None,
        favorite: bool | None = None,
        note: str | None = None,
    ) -> dict[str, object]:
        combination = self.repository.get_saved_combination(combination_id)
        if combination is None:
            raise AppError(
                code=ErrorCode.not_found,
                message="Saved lottery combination was not found.",
                status_code=404,
            )
        updated = self.repository.update_saved_combination(
            combination,
            label=label.strip() if label is not None else None,
            source=source.strip() if source is not None else None,
            favorite=favorite,
            note=note.strip() if note is not None else None,
        )
        self.repository.db.commit()
        self.repository.db.refresh(updated)
        return self._serialize_saved_combination(updated)

    def delete_saved_combination(self, combination_id: int) -> dict[str, object]:
        combination = self.repository.get_saved_combination(combination_id)
        if combination is None:
            raise AppError(
                code=ErrorCode.not_found,
                message="Saved lottery combination was not found.",
                status_code=404,
            )
        self.repository.delete_saved_combination(combination)
        self.repository.db.commit()
        return {"deleted": True, "id": combination_id}

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

    def get_randomness_diagnostics(self, limit: int = 500) -> dict[str, object]:
        draws = [
            self._serialize_draw(draw)
            for draw in self.repository.list_recent_draws(limit=limit)
        ]
        per_draw = [
            self._build_draw_metrics(
                issue_no=str(item["issue_no"]),
                front_numbers=list(item["front_numbers"]),
                back_numbers=list(item["back_numbers"]),
            )
            for item in draws
        ]
        front_rows = [list(item["front_numbers"]) for item in draws]
        back_rows = [list(item["back_numbers"]) for item in draws]
        front_frequency = self._build_randomness_frequency_metric(
            rows=front_rows,
            min_number=1,
            max_number=35,
            picks_per_draw=5,
            area_label="前区",
        )
        back_frequency = self._build_randomness_frequency_metric(
            rows=back_rows,
            min_number=1,
            max_number=12,
            picks_per_draw=2,
            area_label="后区",
        )
        front_sums = [int(item["front_sum"]) for item in reversed(per_draw)]
        front_sum_autocorrelation = self._lag_one_correlation(front_sums)
        notes = [
            "本页用于检查历史开奖序列的统计特征，不用于预测下一期。",
            "p 值为近似计算；样本量不足或多重检验时不要过度解读。",
            "彩票设计目标是随机，局部波动和短期偏离都可能自然出现。",
        ]
        if len(draws) < 100:
            notes.append("当前样本量较小，随机性指标的稳定性有限。")

        return {
            "sample_size": len(draws),
            "requested_limit": limit,
            "latest_issue_no": str(draws[0]["issue_no"]) if draws else None,
            "earliest_issue_no": str(draws[-1]["issue_no"]) if draws else None,
            "front_frequency": front_frequency,
            "back_frequency": back_frequency,
            "front_sum": self._build_sequence_summary(front_sums),
            "front_sum_autocorrelation": {
                "lag": 1,
                "value": front_sum_autocorrelation,
                "interpretation": "接近 0 表示相邻期和值线性相关较弱。",
            },
            "front_parity_distribution": self._summarize_distribution(
                [str(item["front_parity_pattern"]) for item in per_draw]
            ),
            "front_gap_summary": self._build_gap_summary(front_rows),
            "notes": notes,
        }

    def get_co_occurrence_analysis(
        self,
        *,
        area: str = "front",
        limit: int = 500,
        top: int = 30,
    ) -> dict[str, object]:
        if area not in {"front", "back", "cross"}:
            raise AppError(
                code=ErrorCode.validation_error,
                message="Co-occurrence area must be front, back or cross.",
                status_code=422,
            )
        draws = [
            self._serialize_draw(draw)
            for draw in self.repository.list_recent_draws(limit=limit)
        ]
        edges = self._build_co_occurrence_edges(draws=draws, area=area)
        nodes = self._build_co_occurrence_nodes(draws=draws, area=area)
        sorted_edges = sorted(
            edges,
            key=lambda item: (
                -float(item["lift"]),
                -int(item["count"]),
                str(item["source"]),
                str(item["target"]),
            ),
        )[:top]
        return {
            "area": area,
            "sample_size": len(draws),
            "requested_limit": limit,
            "top": top,
            "latest_issue_no": str(draws[0]["issue_no"]) if draws else None,
            "earliest_issue_no": str(draws[-1]["issue_no"]) if draws else None,
            "nodes": nodes,
            "edges": sorted_edges,
            "notes": [
                "共现次数必须和随机期望比较，不能只看绝对出现次数。",
                "lift 大于 1 表示高于随机期望，但不代表未来会继续共同出现。",
                "样本窗口不同会改变共现强度，后续可扩展滚动窗口对比。",
            ],
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

    def get_recommendations(
        self,
        *,
        issue_no: str | None = None,
        sets: int = 5,
        same_period_count: int = 10,
        sample_limit: int = 200,
        same_period_weight: float = 45,
        frequency_weight: float = 25,
        missing_weight: float = 20,
        structure_weight: float = 10,
        co_occurrence_weight: float = 15,
        coverage_weight: float = 16,
    ) -> dict[str, object]:
        latest_draw = self.repository.get_latest_draw()
        if latest_draw is None:
            raise AppError(
                code=ErrorCode.lottery_draw_not_found,
                message="No lottery draw data is available for recommendation analysis.",
                status_code=404,
            )

        target_issue_no = self._resolve_recommendation_issue_no(issue_no, latest_draw.issue_no)
        issue_suffix = target_issue_no[-3:]
        strategy_weights = self._normalize_recommendation_weights(
            same_period_weight=same_period_weight,
            frequency_weight=frequency_weight,
            missing_weight=missing_weight,
            structure_weight=structure_weight,
            co_occurrence_weight=co_occurrence_weight,
            coverage_weight=coverage_weight,
        )
        recent_draws = [
            self._serialize_draw(draw)
            for draw in self.repository.list_recent_draws(limit=sample_limit)
        ]
        same_period_draws = [
            self._serialize_draw(draw)
            for draw in self.repository.list_draws_by_issue_suffix(
                issue_suffix=issue_suffix,
                exclude_issue_no=target_issue_no,
                limit=same_period_count,
            )
        ]
        front_scores = self._score_recommendation_numbers(
            area="front",
            min_number=1,
            max_number=35,
            recent_draws=recent_draws,
            same_period_draws=same_period_draws,
            strategy_weights=strategy_weights,
            co_occurrence_scores=self._build_recommendation_co_occurrence_scores(
                recent_draws=recent_draws,
                area="front",
            ),
        )
        back_scores = self._score_recommendation_numbers(
            area="back",
            min_number=1,
            max_number=12,
            recent_draws=recent_draws,
            same_period_draws=same_period_draws,
            strategy_weights=strategy_weights,
            co_occurrence_scores=self._build_recommendation_co_occurrence_scores(
                recent_draws=recent_draws,
                area="back",
            ),
        )

        return {
            "target_issue_no": target_issue_no,
            "issue_suffix": issue_suffix,
            "sample_size": len(recent_draws),
            "same_period_count": len(same_period_draws),
            "requested_sets": sets,
            "disclaimer": DLT_DISCLAIMER,
            "strategy_weights": strategy_weights,
            "methodology": [
                "历史同期：优先考虑目标期号后三位相同的往年开奖中重复出现的号码。",
                "近期统计：结合最近样本内的出现频次、当前遗漏和冷热状态。",
                "共现参考：观察号码在近期样本中的同期开奖关联强度，并按随机期望校正。",
                "结构约束：参考和值、跨度、奇偶、三区和012路分布，避免结构过于极端。",
                "覆盖分散：多组结果之间控制重合度，尽量扩大前后区号码覆盖面。",
            ],
            "same_period_repeated_front": self._top_recommendation_numbers(
                front_scores,
                limit=10,
            ),
            "same_period_repeated_back": self._top_recommendation_numbers(
                back_scores,
                limit=6,
            ),
            "recommendations": self._build_recommendation_sets(
                front_scores=front_scores,
                back_scores=back_scores,
                recent_draws=recent_draws,
                structure_weight=float(strategy_weights["structure"]),
                coverage_weight=float(strategy_weights["coverage"]),
                limit=sets,
            ),
        }

    def simulate_numbers(
        self,
        *,
        simulations: int = 10000,
        sets: int = 5,
        seed: int | None = None,
    ) -> dict[str, object]:
        latest_draw = self.repository.get_latest_draw()
        if latest_draw is None:
            raise AppError(
                code=ErrorCode.lottery_draw_not_found,
                message="No lottery draw data is available for simulation.",
                status_code=404,
            )

        rng = random.Random(seed)
        front_counts = {number: 0 for number in range(1, 36)}
        back_counts = {number: 0 for number in range(1, 13)}
        generated_sets: list[dict[str, object]] = []

        for index in range(simulations):
            front_numbers = sorted(rng.sample(range(1, 36), 5))
            back_numbers = sorted(rng.sample(range(1, 13), 2))
            for number in front_numbers:
                front_counts[number] += 1
            for number in back_numbers:
                back_counts[number] += 1
            if len(generated_sets) < sets:
                generated_sets.append(
                    self._serialize_simulation_set(
                        rank=len(generated_sets) + 1,
                        front_numbers=front_numbers,
                        back_numbers=back_numbers,
                    )
                )

        return {
            "simulations": simulations,
            "requested_sets": sets,
            "seed": seed,
            "latest_issue_no": latest_draw.issue_no,
            "disclaimer": DLT_DISCLAIMER,
            "methodology": [
                "每次模拟都从前区 1-35 中不放回抽取 5 个号码。",
                "每次模拟都从后区 1-12 中不放回抽取 2 个号码。",
                "模拟结果只反映随机抽样的分布，不使用历史开奖作为预测依据。",
                "号码频率越接近理论概率，说明模拟次数越充分。",
            ],
            "theoretical": {
                "front_probability": round(5 / 35, 6),
                "back_probability": round(2 / 12, 6),
                "jackpot_probability": "1 / 21425712",
                "jackpot_probability_decimal": round(1 / 21425712, 12),
            },
            "generated_sets": generated_sets,
            "front_frequency": self._serialize_simulation_frequency(
                counts=front_counts,
                simulations=simulations,
                expected_probability=5 / 35,
            ),
            "back_frequency": self._serialize_simulation_frequency(
                counts=back_counts,
                simulations=simulations,
                expected_probability=2 / 12,
            ),
        }

    def analyze_combination_coverage(
        self,
        *,
        combinations: list[dict[str, object]],
    ) -> dict[str, object]:
        normalized = self._normalize_coverage_combinations(combinations)
        front_sets = [set(item["front_numbers"]) for item in normalized]
        back_sets = [set(item["back_numbers"]) for item in normalized]
        all_front = [number for item in normalized for number in item["front_numbers"]]
        all_back = [number for item in normalized for number in item["back_numbers"]]
        pairwise = self._build_pairwise_similarity(front_sets=front_sets, back_sets=back_sets)
        front_unique = len(set(all_front))
        back_unique = len(set(all_back))
        set_count = len(normalized)
        return {
            "disclaimer": DLT_DISCLAIMER,
            "set_count": set_count,
            "front_unique_count": front_unique,
            "back_unique_count": back_unique,
            "front_coverage_rate": round(front_unique / 35, 6),
            "back_coverage_rate": round(back_unique / 12, 6),
            "front_duplicate_slots": set_count * 5 - front_unique,
            "back_duplicate_slots": set_count * 2 - back_unique,
            "front_entropy": self._normalized_entropy(all_front, 35),
            "back_entropy": self._normalized_entropy(all_back, 12),
            "average_jaccard": round(mean(item["combined_jaccard"] for item in pairwise), 6)
            if pairwise
            else 0,
            "max_jaccard": max((item["combined_jaccard"] for item in pairwise), default=0),
            "min_front_distance": min(
                self._minimum_number_distance(item["front_numbers"]) for item in normalized
            ),
            "zone_coverage": self._build_zone_coverage(all_front),
            "parity_coverage": self._build_parity_coverage(all_front, all_back),
            "size_coverage": self._build_size_coverage(all_front, all_back),
            "tail_coverage": self._build_tail_coverage(all_front, all_back),
            "combinations": [
                {
                    **item,
                    **self._build_coverage_combination_metrics(
                        front_numbers=item["front_numbers"],
                        back_numbers=item["back_numbers"],
                    ),
                }
                for item in normalized
            ],
            "pairwise_similarity": pairwise,
            "notes": [
                "最大熵/组合覆盖只衡量多组号码的分散度和覆盖结构，不能提高单注中奖概率。",
                "Jaccard 越高表示两组越相似；如果多组号码过于相似，覆盖面会变窄。",
                "覆盖率越高表示这批样本触达的号码更多，但不代表这些号码更可能开奖。",
                "建议把它作为组合筛选和回测前的体检工具，而不是预测工具。",
            ],
        }

    def analyze_dantuo(
        self,
        *,
        front_dan: list[int],
        front_tuo: list[int],
        front_kill: list[int],
        back_dan: list[int],
        back_tuo: list[int],
        back_kill: list[int],
        addon: bool = False,
        preview_limit: int = 20,
    ) -> dict[str, object]:
        front_dan = self._normalize_number_list(front_dan)
        front_tuo = self._normalize_number_list(front_tuo)
        front_kill = self._normalize_number_list(front_kill)
        back_dan = self._normalize_number_list(back_dan)
        back_tuo = self._normalize_number_list(back_tuo)
        back_kill = self._normalize_number_list(back_kill)

        self._validate_dantuo_area(
            area_label="front",
            dan=front_dan,
            tuo=front_tuo,
            kill=front_kill,
            min_number=1,
            max_number=35,
            required_count=5,
        )
        self._validate_dantuo_area(
            area_label="back",
            dan=back_dan,
            tuo=back_tuo,
            kill=back_kill,
            min_number=1,
            max_number=12,
            required_count=2,
        )

        front_required = 5 - len(front_dan)
        back_required = 2 - len(back_dan)
        front_combination_count = comb(len(front_tuo), front_required)
        back_combination_count = comb(len(back_tuo), back_required)
        total_bets = front_combination_count * back_combination_count
        base_cost = total_bets * 2
        addon_cost = total_bets if addon else 0
        preview = self._build_dantuo_preview(
            front_dan=front_dan,
            front_tuo=front_tuo,
            front_required=front_required,
            back_dan=back_dan,
            back_tuo=back_tuo,
            back_required=back_required,
            limit=preview_limit,
        )

        warnings: list[str] = []
        if total_bets >= 500:
            warnings.append("注数较高，建议先缩小拖码范围或减少胆码不确定性。")
        if front_kill:
            warnings.append("前区杀号已从可选池排除，但杀号本身不代表号码一定不会出现。")
        if back_kill:
            warnings.append("后区杀号已从可选池排除，但后区波动更大，建议谨慎使用。")

        return {
            "disclaimer": DLT_DISCLAIMER,
            "addon": addon,
            "front_required": front_required,
            "back_required": back_required,
            "front_combination_count": front_combination_count,
            "back_combination_count": back_combination_count,
            "total_bets": total_bets,
            "base_cost": base_cost,
            "addon_cost": addon_cost,
            "total_cost": base_cost + addon_cost,
            "front_dan": front_dan,
            "front_tuo": front_tuo,
            "front_kill": front_kill,
            "back_dan": back_dan,
            "back_tuo": back_tuo,
            "back_kill": back_kill,
            "available_front": [
                number for number in range(1, 36) if number not in set(front_kill)
            ],
            "available_back": [
                number for number in range(1, 13) if number not in set(back_kill)
            ],
            "preview_limit": preview_limit,
            "preview": preview,
            "warnings": warnings,
            "methodology": [
                "胆码：你认为更值得保留的号码，计算时每一注都会包含它。",
                "拖码：和胆码一起组合的候选号码，系统按组合数学展开。",
                "杀号：从可选池中排除的号码，只作为人工辅助，不代表确定不会开奖。",
                "注数 = 前区组合数 x 后区组合数；普通投注每注 2 元，追加每注再加 1 元。",
            ],
        }

    def backtest_numbers(
        self,
        *,
        front_numbers: list[int],
        back_numbers: list[int],
        addon: bool = False,
        hit_limit: int = 20,
    ) -> dict[str, object]:
        front_numbers = self._normalize_number_list(front_numbers)
        back_numbers = self._normalize_number_list(back_numbers)
        self._validate_exact_numbers(
            area_label="front",
            numbers=front_numbers,
            min_number=1,
            max_number=35,
            required_count=5,
        )
        self._validate_exact_numbers(
            area_label="back",
            numbers=back_numbers,
            min_number=1,
            max_number=12,
            required_count=2,
        )

        rule = self.repository.get_current_rule()
        if rule is None:
            raise AppError(
                code=ErrorCode.lottery_rule_not_found,
                message="Current lottery rule was not found.",
                status_code=404,
            )
        draws = [self._serialize_draw(draw) for draw in self.repository.list_all_draws()]
        if not draws:
            raise AppError(
                code=ErrorCode.lottery_draw_not_found,
                message="No lottery draw data is available for backtesting.",
                status_code=404,
            )

        prize_map = {
            (tier.front_match_count, tier.back_match_count): tier
            for tier in rule.prize_tiers
        }
        distribution = {
            f"{front}+{back}": {
                "match_key": f"{front}+{back}",
                "front_match_count": front,
                "back_match_count": back,
                "count": 0,
                "prize_tier": prize_map.get((front, back)).tier
                if (front, back) in prize_map
                else None,
                "tier_name": prize_map.get((front, back)).tier_name
                if (front, back) in prize_map
                else "未中奖",
            }
            for front in range(5, -1, -1)
            for back in range(2, -1, -1)
        }
        hits: list[dict[str, object]] = []
        fixed_prize_return = 0
        floating_hit_count = 0

        selected_front = set(front_numbers)
        selected_back = set(back_numbers)
        for draw in draws:
            front_match_count = len(selected_front & set(draw["front_numbers"]))
            back_match_count = len(selected_back & set(draw["back_numbers"]))
            match_key = f"{front_match_count}+{back_match_count}"
            distribution[match_key]["count"] += 1
            prize_tier = prize_map.get((front_match_count, back_match_count))
            if prize_tier is None:
                continue

            base_prize_amount = (
                int(prize_tier.base_prize_amount)
                if prize_tier.base_prize_amount is not None
                else None
            )
            if base_prize_amount is None:
                floating_hit_count += 1
            else:
                fixed_prize_return += base_prize_amount
            hit = {
                "issue_no": draw["issue_no"],
                "draw_date": draw["draw_date"],
                "draw_front_numbers": draw["front_numbers"],
                "draw_back_numbers": draw["back_numbers"],
                "front_matches": sorted(selected_front & set(draw["front_numbers"])),
                "back_matches": sorted(selected_back & set(draw["back_numbers"])),
                "front_match_count": front_match_count,
                "back_match_count": back_match_count,
                "match_key": match_key,
                "prize_tier": prize_tier.tier,
                "tier_name": prize_tier.tier_name,
                "is_floating": prize_tier.is_floating,
                "base_prize_amount": base_prize_amount,
            }
            hits.append(hit)

        hits.sort(
            key=lambda item: (
                int(item["prize_tier"]),
                -int(item["front_match_count"]),
                -int(item["back_match_count"]),
                str(item["issue_no"]),
            )
        )
        latest_hit = max(hits, key=lambda item: str(item["issue_no"])) if hits else None
        highest_hit = hits[0] if hits else None
        total_cost = len(draws) * (3 if addon else 2)
        base_cost = len(draws) * 2
        addon_cost = len(draws) if addon else 0
        return {
            "disclaimer": DLT_DISCLAIMER,
            "front_numbers": front_numbers,
            "back_numbers": back_numbers,
            "addon": addon,
            "sample_size": len(draws),
            "earliest_issue_no": draws[-1]["issue_no"],
            "latest_issue_no": draws[0]["issue_no"],
            "base_cost": base_cost,
            "addon_cost": addon_cost,
            "total_cost": total_cost,
            "fixed_prize_return": fixed_prize_return,
            "floating_hit_count": floating_hit_count,
            "net_fixed_result": fixed_prize_return - total_cost,
            "hit_count": len(hits),
            "no_prize_count": len(draws) - len(hits),
            "highest_hit": highest_hit,
            "latest_hit": latest_hit,
            "hit_preview_limit": hit_limit,
            "hits": hits[:hit_limit],
            "distribution": sorted(
                distribution.values(),
                key=lambda item: (
                    -int(item["front_match_count"]),
                    -int(item["back_match_count"]),
                ),
            ),
            "methodology": [
                "把你输入的 5 个前区和 2 个后区，逐期与历史开奖号码做交集。",
                "每期得到一个命中结构，例如 3+1 表示前区命中 3 个、后区命中 1 个。",
                "命中结构再按当前官方奖级表换算奖级；浮动奖只统计次数，不估算奖金。",
                "成本按每期买 1 注计算：普通 2 元，勾选追加后按 3 元。",
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

    @staticmethod
    def _resolve_recommendation_issue_no(issue_no: str | None, latest_issue_no: str) -> str:
        normalized = issue_no.strip() if issue_no is not None else None
        if normalized:
            if len(normalized) == 3 and normalized.isdigit():
                prefix = latest_issue_no[:-3] if len(latest_issue_no) > 3 else ""
                return f"{prefix}{normalized}"
            return normalized
        if latest_issue_no.isdigit():
            return str(int(latest_issue_no) + 1).zfill(len(latest_issue_no))
        return latest_issue_no

    @classmethod
    def _serialize_simulation_set(
        cls,
        *,
        rank: int,
        front_numbers: list[int],
        back_numbers: list[int],
    ) -> dict[str, object]:
        metrics = cls._build_draw_metrics(
            issue_no="simulation",
            front_numbers=front_numbers,
            back_numbers=back_numbers,
        )
        return {
            "rank": rank,
            "front_numbers": front_numbers,
            "back_numbers": back_numbers,
            "front_sum": metrics["front_sum"],
            "front_span": metrics["front_span"],
            "front_parity_pattern": metrics["front_parity_pattern"],
            "front_zone_pattern": metrics["front_zone_pattern"],
            "front_route012_pattern": metrics["front_route012_pattern"],
        }

    @staticmethod
    def _serialize_simulation_frequency(
        *,
        counts: dict[int, int],
        simulations: int,
        expected_probability: float,
    ) -> list[dict[str, object]]:
        return [
            {
                "number": number,
                "count": count,
                "frequency": round(count / simulations, 6),
                "expected_probability": round(expected_probability, 6),
                "deviation": round(count / simulations - expected_probability, 6),
            }
            for number, count in sorted(
                counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

    @classmethod
    def _normalize_coverage_combinations(
        cls,
        combinations: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        if len(combinations) < 2:
            raise AppError(
                code=ErrorCode.validation_error,
                message="At least two combinations are required for coverage analysis.",
                status_code=422,
            )
        normalized: list[dict[str, object]] = []
        seen_signatures: set[str] = set()
        for index, item in enumerate(combinations, start=1):
            front_numbers = cls._normalize_number_list(list(item["front_numbers"]))
            back_numbers = cls._normalize_number_list(list(item["back_numbers"]))
            cls._validate_exact_numbers(
                area_label="front",
                numbers=front_numbers,
                min_number=1,
                max_number=35,
                required_count=5,
            )
            cls._validate_exact_numbers(
                area_label="back",
                numbers=back_numbers,
                min_number=1,
                max_number=12,
                required_count=2,
            )
            signature = f"{','.join(map(str, front_numbers))}|{','.join(map(str, back_numbers))}"
            if signature in seen_signatures:
                raise AppError(
                    code=ErrorCode.validation_error,
                    message="Duplicate combinations are not allowed in coverage analysis.",
                    status_code=422,
                )
            seen_signatures.add(signature)
            normalized.append(
                {
                    "rank": index,
                    "front_numbers": front_numbers,
                    "back_numbers": back_numbers,
                }
            )
        return normalized

    @staticmethod
    def _normalized_entropy(numbers: list[int], domain_size: int) -> dict[str, float]:
        counts = Counter(numbers)
        total = len(numbers)
        entropy = 0.0
        if total:
            entropy = -sum(
                (count / total) * log2(count / total)
                for count in counts.values()
                if count > 0
            )
        max_entropy = log2(domain_size)
        return {
            "value": round(entropy, 6),
            "max": round(max_entropy, 6),
            "normalized": round(entropy / max_entropy, 6) if max_entropy else 0,
        }

    @staticmethod
    def _build_pairwise_similarity(
        *,
        front_sets: list[set[int]],
        back_sets: list[set[int]],
    ) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        for left_index, right_index in combinations(range(len(front_sets)), 2):
            front_union = front_sets[left_index] | front_sets[right_index]
            back_union = back_sets[left_index] | back_sets[right_index]
            combined_left = {f"f-{number}" for number in front_sets[left_index]} | {
                f"b-{number}" for number in back_sets[left_index]
            }
            combined_right = {f"f-{number}" for number in front_sets[right_index]} | {
                f"b-{number}" for number in back_sets[right_index]
            }
            combined_union = combined_left | combined_right
            combined_intersection = combined_left & combined_right
            front_jaccard = len(front_sets[left_index] & front_sets[right_index]) / len(front_union)
            back_jaccard = len(back_sets[left_index] & back_sets[right_index]) / len(back_union)
            combined_jaccard = (
                len(combined_intersection) / len(combined_union) if combined_union else 0
            )
            items.append(
                {
                    "left_rank": left_index + 1,
                    "right_rank": right_index + 1,
                    "front_overlap": len(front_sets[left_index] & front_sets[right_index]),
                    "back_overlap": len(back_sets[left_index] & back_sets[right_index]),
                    "front_jaccard": round(front_jaccard, 6),
                    "back_jaccard": round(back_jaccard, 6),
                    "combined_jaccard": round(combined_jaccard, 6),
                }
            )
        return sorted(items, key=lambda item: (-float(item["combined_jaccard"]), item["left_rank"]))

    @staticmethod
    def _minimum_number_distance(numbers: list[int]) -> int:
        sorted_numbers = sorted(numbers)
        return min(
            right - left
            for left, right in zip(sorted_numbers, sorted_numbers[1:], strict=False)
        )

    @classmethod
    def _build_coverage_combination_metrics(
        cls,
        *,
        front_numbers: list[int],
        back_numbers: list[int],
    ) -> dict[str, object]:
        metrics = cls._build_draw_metrics(
            issue_no="coverage",
            front_numbers=front_numbers,
            back_numbers=back_numbers,
        )
        return {
            "front_sum": metrics["front_sum"],
            "front_span": metrics["front_span"],
            "front_parity_pattern": metrics["front_parity_pattern"],
            "front_zone_pattern": metrics["front_zone_pattern"],
            "front_route012_pattern": metrics["front_route012_pattern"],
            "front_min_distance": cls._minimum_number_distance(front_numbers),
        }

    @staticmethod
    def _build_zone_coverage(numbers: list[int]) -> dict[str, int]:
        unique_numbers = set(numbers)
        return {
            "zone_1_12": sum(1 for number in unique_numbers if 1 <= number <= 12),
            "zone_13_24": sum(1 for number in unique_numbers if 13 <= number <= 24),
            "zone_25_35": sum(1 for number in unique_numbers if 25 <= number <= 35),
        }

    @staticmethod
    def _build_parity_coverage(front_numbers: list[int], back_numbers: list[int]) -> dict[str, int]:
        return {
            "front_odd": sum(1 for number in front_numbers if number % 2 == 1),
            "front_even": sum(1 for number in front_numbers if number % 2 == 0),
            "back_odd": sum(1 for number in back_numbers if number % 2 == 1),
            "back_even": sum(1 for number in back_numbers if number % 2 == 0),
        }

    @staticmethod
    def _build_size_coverage(front_numbers: list[int], back_numbers: list[int]) -> dict[str, int]:
        return {
            "front_small": sum(1 for number in front_numbers if number <= 17),
            "front_large": sum(1 for number in front_numbers if number >= 18),
            "back_small": sum(1 for number in back_numbers if number <= 6),
            "back_large": sum(1 for number in back_numbers if number >= 7),
        }

    @staticmethod
    def _build_tail_coverage(front_numbers: list[int], back_numbers: list[int]) -> dict[str, int]:
        return {
            "front_unique_tails": len({number % 10 for number in front_numbers}),
            "back_unique_tails": len({number % 10 for number in back_numbers}),
        }

    @staticmethod
    def _normalize_number_list(numbers: list[int]) -> list[int]:
        return sorted(set(numbers))

    @staticmethod
    def _validate_dantuo_area(
        *,
        area_label: str,
        dan: list[int],
        tuo: list[int],
        kill: list[int],
        min_number: int,
        max_number: int,
        required_count: int,
    ) -> None:
        all_numbers = [*dan, *tuo, *kill]
        invalid_numbers = [
            number for number in all_numbers if number < min_number or number > max_number
        ]
        if invalid_numbers:
            raise AppError(
                code=ErrorCode.validation_error,
                message=(
                    f"Lottery {area_label} numbers must be between "
                    f"{min_number} and {max_number}."
                ),
                status_code=422,
            )

        if set(dan) & set(tuo) or set(dan) & set(kill) or set(tuo) & set(kill):
            raise AppError(
                code=ErrorCode.validation_error,
                message=f"Lottery {area_label} dan, tuo and kill numbers cannot overlap.",
                status_code=422,
            )

        if len(dan) >= required_count:
            raise AppError(
                code=ErrorCode.validation_error,
                message=(
                    f"Lottery {area_label} dan count must be less than "
                    f"{required_count} for dantuo analysis."
                ),
                status_code=422,
            )

        needed = required_count - len(dan)
        if len(tuo) < needed:
            raise AppError(
                code=ErrorCode.validation_error,
                message=(
                    f"Lottery {area_label} tuo count must be at least {needed} "
                    "after dan numbers are selected."
                ),
                status_code=422,
            )

    @staticmethod
    def _validate_exact_numbers(
        *,
        area_label: str,
        numbers: list[int],
        min_number: int,
        max_number: int,
        required_count: int,
    ) -> None:
        if len(numbers) != required_count:
            raise AppError(
                code=ErrorCode.validation_error,
                message=(
                    f"Lottery {area_label} numbers must contain exactly "
                    f"{required_count} unique numbers."
                ),
                status_code=422,
            )
        invalid_numbers = [
            number for number in numbers if number < min_number or number > max_number
        ]
        if invalid_numbers:
            raise AppError(
                code=ErrorCode.validation_error,
                message=(
                    f"Lottery {area_label} numbers must be between "
                    f"{min_number} and {max_number}."
                ),
                status_code=422,
            )

    @staticmethod
    def _build_dantuo_preview(
        *,
        front_dan: list[int],
        front_tuo: list[int],
        front_required: int,
        back_dan: list[int],
        back_tuo: list[int],
        back_required: int,
        limit: int,
    ) -> list[dict[str, object]]:
        preview: list[dict[str, object]] = []
        rank = 1
        for front_tail in combinations(front_tuo, front_required):
            front_numbers = sorted([*front_dan, *front_tail])
            for back_tail in combinations(back_tuo, back_required):
                back_numbers = sorted([*back_dan, *back_tail])
                metrics = LotteryService._build_draw_metrics(
                    issue_no="dantuo",
                    front_numbers=front_numbers,
                    back_numbers=back_numbers,
                )
                preview.append(
                    {
                        "rank": rank,
                        "front_numbers": front_numbers,
                        "back_numbers": back_numbers,
                        "front_sum": metrics["front_sum"],
                        "front_span": metrics["front_span"],
                        "front_parity_pattern": metrics["front_parity_pattern"],
                        "front_zone_pattern": metrics["front_zone_pattern"],
                        "front_route012_pattern": metrics["front_route012_pattern"],
                    }
                )
                rank += 1
                if len(preview) >= limit:
                    return preview
        return preview

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
        sync_details: list[dict[str, str]] = []
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
                sync_details.append(
                    {
                        "issue_no": record.issue_no,
                        "draw_date": record.draw_date.isoformat(),
                        "action": action,
                    }
                )
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
                raw_metadata={
                    **source_page.raw_metadata,
                    "details": sync_details,
                },
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
                raw_metadata={"details": sync_details},
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
                raw_metadata={"details": sync_details},
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
    def _normalize_recommendation_weights(
        *,
        same_period_weight: float,
        frequency_weight: float,
        missing_weight: float,
        structure_weight: float,
        co_occurrence_weight: float = 15,
        coverage_weight: float = 16,
    ) -> dict[str, float]:
        weights = {
            "same_period": max(0.0, same_period_weight),
            "frequency": max(0.0, frequency_weight),
            "missing": max(0.0, missing_weight),
            "structure": max(0.0, structure_weight),
            "co_occurrence": max(0.0, co_occurrence_weight),
            "coverage": max(0.0, coverage_weight),
        }
        if sum(weights.values()) <= 0:
            return {
                "same_period": 45.0,
                "frequency": 25.0,
                "missing": 20.0,
                "structure": 10.0,
                "co_occurrence": 15.0,
                "coverage": 16.0,
            }
        return {key: round(value, 2) for key, value in weights.items()}

    @classmethod
    def _build_recommendation_co_occurrence_scores(
        cls,
        *,
        recent_draws: list[dict[str, object]],
        area: str,
    ) -> dict[int, float]:
        edges = cls._build_co_occurrence_edges(draws=recent_draws, area=area)
        prefix = f"{area}-"
        scores: dict[int, float] = Counter()
        for edge in edges:
            lift = max(0.0, float(edge["lift"]) - 1)
            if lift <= 0:
                continue
            for key in ("source", "target"):
                node_id = str(edge[key])
                if node_id.startswith(prefix):
                    number = int(node_id.removeprefix(prefix))
                    scores[number] += lift
        return dict(scores)

    @classmethod
    def _score_recommendation_numbers(
        cls,
        *,
        area: str,
        min_number: int,
        max_number: int,
        recent_draws: list[dict[str, object]],
        same_period_draws: list[dict[str, object]],
        strategy_weights: dict[str, float],
        co_occurrence_scores: dict[int, float] | None = None,
    ) -> list[dict[str, object]]:
        recent_rows = [list(draw[f"{area}_numbers"]) for draw in recent_draws]
        if not recent_rows:
            return []
        co_occurrence_scores = co_occurrence_scores or {}

        same_period_rows = [list(draw[f"{area}_numbers"]) for draw in same_period_draws]
        issue_numbers = [str(draw["issue_no"]) for draw in recent_draws]
        frequency_items = cls._build_frequency(
            rows=recent_rows,
            min_number=min_number,
            max_number=max_number,
            recent_issue_numbers=issue_numbers,
        )
        frequency_by_number = {int(item["number"]): item for item in frequency_items}
        same_counts = {
            number: sum(1 for row in same_period_rows if number in row)
            for number in range(min_number, max_number + 1)
        }
        max_same_count = max(same_counts.values(), default=0) or 1
        max_frequency = max((int(item["count"]) for item in frequency_items), default=0) or 1
        max_co_occurrence = max(co_occurrence_scores.values(), default=0) or 1
        expected_gap = max(
            1,
            round(len(recent_rows) / ((max_number - min_number + 1) / len(recent_rows[0]))),
        )
        scored: list[dict[str, object]] = []

        for number in range(min_number, max_number + 1):
            frequency = int(frequency_by_number[number]["count"])
            missing = int(frequency_by_number[number]["missing"])
            same_hits = same_counts[number]
            same_score = strategy_weights["same_period"] * (same_hits / max_same_count)
            frequency_score = strategy_weights["frequency"] * (frequency / max_frequency)
            missing_score = strategy_weights["missing"] * min(missing / expected_gap, 1.25)
            co_occurrence_raw = co_occurrence_scores.get(number, 0.0)
            co_occurrence_score = (
                strategy_weights["co_occurrence"] * (co_occurrence_raw / max_co_occurrence)
            )
            balance_score = 6 if same_hits >= 1 or missing <= expected_gap * 2 else 2
            score = round(
                same_score
                + frequency_score
                + missing_score
                + co_occurrence_score
                + balance_score,
                2,
            )
            scored.append(
                {
                    "number": number,
                    "score": score,
                    "same_period_hits": same_hits,
                    "recent_frequency": frequency,
                    "current_missing": missing,
                    "co_occurrence_score": round(co_occurrence_raw, 4),
                    "reasons": cls._build_number_reasons(
                        same_hits=same_hits,
                        frequency=frequency,
                        missing=missing,
                        expected_gap=expected_gap,
                        co_occurrence_score=co_occurrence_raw,
                    ),
                }
            )

        return sorted(scored, key=lambda item: (-float(item["score"]), int(item["number"])))

    @staticmethod
    def _build_number_reasons(
        *,
        same_hits: int,
        frequency: int,
        missing: int,
        expected_gap: int,
        co_occurrence_score: float,
    ) -> list[str]:
        reasons: list[str] = []
        if same_hits > 0:
            reasons.append(f"历史同期出现 {same_hits} 次")
        if frequency > 0:
            reasons.append(f"近期样本出现 {frequency} 次")
        if co_occurrence_score >= 1.2:
            reasons.append(f"近期共现强度 {round(co_occurrence_score, 2)}，高于随机期望")
        if missing >= expected_gap:
            reasons.append(f"当前遗漏 {missing} 期，高于理论间隔约 {expected_gap} 期")
        elif missing <= 2:
            reasons.append("近期刚出现，偏热")
        else:
            reasons.append(f"当前遗漏 {missing} 期，处于中间区间")
        return reasons

    @classmethod
    def _build_recommendation_sets(
        cls,
        *,
        front_scores: list[dict[str, object]],
        back_scores: list[dict[str, object]],
        recent_draws: list[dict[str, object]],
        structure_weight: float,
        limit: int,
        coverage_weight: float = 0,
    ) -> list[dict[str, object]]:
        if not front_scores or not back_scores or not recent_draws:
            return []

        front_pool = [int(item["number"]) for item in front_scores[:14]]
        back_pool = [int(item["number"]) for item in back_scores[:7]]
        front_score_map = {int(item["number"]): item for item in front_scores}
        back_score_map = {int(item["number"]): item for item in back_scores}
        historical_metrics = [
            cls._build_draw_metrics(
                issue_no=str(draw["issue_no"]),
                front_numbers=list(draw["front_numbers"]),
                back_numbers=list(draw["back_numbers"]),
            )
            for draw in recent_draws[:120]
        ]
        sum_average = mean([int(item["front_sum"]) for item in historical_metrics])
        span_average = mean([int(item["front_span"]) for item in historical_metrics])
        candidates: list[dict[str, object]] = []

        for front_combo in combinations(front_pool, 5):
            front_numbers = sorted(front_combo)
            metrics = cls._build_draw_metrics(
                issue_no="candidate",
                front_numbers=front_numbers,
                back_numbers=[],
            )
            front_structure_score = cls._score_front_structure(
                front_numbers=front_numbers,
                metrics=metrics,
                sum_average=sum_average,
                span_average=span_average,
            )
            for back_combo in combinations(back_pool, 2):
                back_numbers = sorted(back_combo)
                number_score = sum(
                    float(front_score_map[number]["score"]) for number in front_numbers
                ) + sum(float(back_score_map[number]["score"]) for number in back_numbers)
                candidates.append(
                    {
                        "front_numbers": front_numbers,
                        "back_numbers": back_numbers,
                        "score": round(
                            number_score + front_structure_score * (structure_weight / 10),
                            2,
                        ),
                        "metrics": metrics,
                        "coverage_note": "首组按综合评分优先选择。",
                    }
                )

        selected: list[dict[str, object]] = []
        remaining = sorted(candidates, key=lambda item: -float(item["score"]))[:1500]
        while remaining and len(selected) < limit:
            ranked_candidates = sorted(
                remaining,
                key=lambda item: -cls._score_candidate_with_coverage(
                    candidate=item,
                    selected=selected,
                    coverage_weight=coverage_weight,
                ),
            )
            candidate = ranked_candidates[0]
            remaining.remove(candidate)
            if cls._is_recommendation_too_similar(candidate, selected):
                continue
            coverage_metrics = cls._build_candidate_coverage_metrics(candidate, selected)
            candidate["score"] = round(
                cls._score_candidate_with_coverage(
                    candidate=candidate,
                    selected=selected,
                    coverage_weight=coverage_weight,
                ),
                2,
            )
            candidate["coverage_note"] = cls._build_candidate_coverage_note(coverage_metrics)
            selected.append(candidate)

        return [
            cls._serialize_recommendation_set(
                rank=index,
                candidate=candidate,
                front_score_map=front_score_map,
                back_score_map=back_score_map,
                sum_average=sum_average,
                span_average=span_average,
            )
            for index, candidate in enumerate(selected, start=1)
        ]

    @staticmethod
    def _score_front_structure(
        *,
        front_numbers: list[int],
        metrics: dict[str, object],
        sum_average: float,
        span_average: float,
    ) -> float:
        front_sum = int(metrics["front_sum"])
        front_span = int(metrics["front_span"])
        score = max(0, 18 - abs(front_sum - sum_average) * 0.75)
        score += max(0, 12 - abs(front_span - span_average) * 0.8)
        odd_count = sum(1 for number in front_numbers if number % 2 == 1)
        if odd_count in {2, 3}:
            score += 10
        if all(count > 0 for count in list(metrics["front_zone_counts"])):
            score += 8
        if all(count > 0 for count in list(metrics["front_route012_counts"])):
            score += 6
        return round(score, 2)

    @classmethod
    def _score_candidate_with_coverage(
        cls,
        *,
        candidate: dict[str, object],
        selected: list[dict[str, object]],
        coverage_weight: float,
    ) -> float:
        base_score = float(candidate["score"])
        if not selected or coverage_weight <= 0:
            return base_score
        metrics = cls._build_candidate_coverage_metrics(candidate, selected)
        coverage_score = (
            (1 - float(metrics["max_jaccard"])) * 12
            + int(metrics["new_front_count"]) * 2.2
            + int(metrics["new_back_count"]) * 5.0
        )
        if int(metrics["new_front_count"]) == 0:
            coverage_score -= 10
        if int(metrics["new_back_count"]) == 0:
            coverage_score -= 8
        return base_score + coverage_score * (coverage_weight / 10)

    @staticmethod
    def _build_candidate_coverage_metrics(
        candidate: dict[str, object],
        selected: list[dict[str, object]],
    ) -> dict[str, object]:
        candidate_front = set(candidate["front_numbers"])
        candidate_back = set(candidate["back_numbers"])
        used_front = {
            number for item in selected for number in set(item["front_numbers"])
        }
        used_back = {
            number for item in selected for number in set(item["back_numbers"])
        }
        jaccards: list[float] = []
        for item in selected:
            combined_candidate = {f"f-{number}" for number in candidate_front} | {
                f"b-{number}" for number in candidate_back
            }
            combined_item = {f"f-{number}" for number in set(item["front_numbers"])} | {
                f"b-{number}" for number in set(item["back_numbers"])
            }
            union = combined_candidate | combined_item
            jaccards.append(len(combined_candidate & combined_item) / len(union) if union else 0)
        return {
            "new_front_count": len(candidate_front - used_front),
            "new_back_count": len(candidate_back - used_back),
            "max_jaccard": round(max(jaccards, default=0), 6),
        }

    @staticmethod
    def _build_candidate_coverage_note(metrics: dict[str, object]) -> str:
        return (
            f"与已选组合最高 Jaccard {metrics['max_jaccard']}，"
            f"新增前区 {metrics['new_front_count']} 个、后区 {metrics['new_back_count']} 个覆盖点。"
        )

    @staticmethod
    def _is_recommendation_too_similar(
        candidate: dict[str, object],
        selected: list[dict[str, object]],
    ) -> bool:
        front_numbers = set(candidate["front_numbers"])
        back_numbers = set(candidate["back_numbers"])
        for item in selected:
            front_overlap = len(front_numbers & set(item["front_numbers"]))
            back_overlap = len(back_numbers & set(item["back_numbers"]))
            if front_overlap >= 5:
                return True
            if front_overlap >= 4 and back_overlap >= 1:
                return True
            if front_overlap >= 2 and back_overlap >= 2:
                return True
        return False

    @classmethod
    def _serialize_recommendation_set(
        cls,
        *,
        rank: int,
        candidate: dict[str, object],
        front_score_map: dict[int, dict[str, object]],
        back_score_map: dict[int, dict[str, object]],
        sum_average: float,
        span_average: float,
    ) -> dict[str, object]:
        front_numbers = list(candidate["front_numbers"])
        back_numbers = list(candidate["back_numbers"])
        metrics = candidate["metrics"]
        return {
            "rank": rank,
            "front_numbers": front_numbers,
            "back_numbers": back_numbers,
            "score": candidate["score"],
            "rationale": cls._build_set_rationale(
                front_numbers=front_numbers,
                back_numbers=back_numbers,
                front_score_map=front_score_map,
                back_score_map=back_score_map,
                metrics=metrics,
                sum_average=sum_average,
                span_average=span_average,
                coverage_note=str(candidate["coverage_note"]),
            ),
            "front_sum": metrics["front_sum"],
            "front_span": metrics["front_span"],
            "front_parity_pattern": metrics["front_parity_pattern"],
            "front_zone_pattern": metrics["front_zone_pattern"],
            "front_route012_pattern": metrics["front_route012_pattern"],
            "front_details": [front_score_map[number] for number in front_numbers],
            "back_details": [back_score_map[number] for number in back_numbers],
        }

    @staticmethod
    def _build_set_rationale(
        *,
        front_numbers: list[int],
        back_numbers: list[int],
        front_score_map: dict[int, dict[str, object]],
        back_score_map: dict[int, dict[str, object]],
        metrics: dict[str, object],
        sum_average: float,
        span_average: float,
        coverage_note: str,
    ) -> list[str]:
        same_front = [
            number
            for number in front_numbers
            if int(front_score_map[number]["same_period_hits"]) > 0
        ]
        same_back = [
            number
            for number in back_numbers
            if int(back_score_map[number]["same_period_hits"]) > 0
        ]
        hot_front = [
            number
            for number in front_numbers
            if int(front_score_map[number]["current_missing"]) <= 2
        ]
        missing_front = [
            number
            for number in front_numbers
            if int(front_score_map[number]["current_missing"]) >= 10
        ]
        return [
            f"前区和值 {metrics['front_sum']}，接近近期均值 {round(sum_average, 1)}。",
            f"前区跨度 {metrics['front_span']}，近期平均跨度约 {round(span_average, 1)}。",
            (
                f"奇偶结构 {metrics['front_parity_pattern']}，"
                f"三区 {metrics['front_zone_pattern']}，012路 {metrics['front_route012_pattern']}。"
            ),
            f"包含历史同期重复号：前区 {same_front or '无'}，后区 {same_back or '无'}。",
            f"冷热搭配：近期热号 {hot_front or '无'}，较高遗漏号 {missing_front or '无'}。",
            f"覆盖分散：{coverage_note}",
        ]

    @staticmethod
    def _top_recommendation_numbers(
        scored_numbers: list[dict[str, object]],
        *,
        limit: int,
    ) -> list[dict[str, object]]:
        return sorted(
            scored_numbers,
            key=lambda item: (
                -int(item["same_period_hits"]),
                -float(item["score"]),
                int(item["number"]),
            ),
        )[:limit]

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
    def _build_randomness_frequency_metric(
        *,
        rows: list[list[int]],
        min_number: int,
        max_number: int,
        picks_per_draw: int,
        area_label: str,
    ) -> dict[str, object]:
        counts = Counter(number for row in rows for number in row)
        sample_size = len(rows)
        number_count = max_number - min_number + 1
        expected = sample_size * picks_per_draw / number_count if number_count else 0
        chi_square = sum(
            ((counts[number] - expected) ** 2 / expected) if expected else 0
            for number in range(min_number, max_number + 1)
        )
        degrees = number_count - 1
        p_value = LotteryService._chi_square_survival_approx(chi_square, degrees)
        deviations = [
            {
                "number": number,
                "count": counts[number],
                "expected": round(expected, 2),
                "deviation": round(counts[number] - expected, 2),
            }
            for number in range(min_number, max_number + 1)
        ]
        return {
            "area": area_label,
            "sample_size": sample_size,
            "total_observations": sample_size * picks_per_draw,
            "chi_square": round(chi_square, 4),
            "degrees_of_freedom": degrees,
            "p_value": p_value,
            "p_value_method": "Wilson-Hilferty normal approximation",
            "entropy": LotteryService._frequency_entropy(counts, min_number, max_number),
            "top_deviations": sorted(
                deviations,
                key=lambda item: abs(float(item["deviation"])),
                reverse=True,
            )[:8],
            "interpretation": "卡方统计量越大，号码频率与均匀分布差异越大。",
        }

    @staticmethod
    def _chi_square_survival_approx(chi_square: float, degrees_of_freedom: int) -> float:
        if degrees_of_freedom <= 0 or chi_square < 0:
            return 0
        if chi_square == 0:
            return 1
        z_score = (
            (chi_square / degrees_of_freedom) ** (1 / 3)
            - (1 - 2 / (9 * degrees_of_freedom))
        ) / sqrt(2 / (9 * degrees_of_freedom))
        return round(max(0, min(1, 0.5 * (1 - erf(z_score / sqrt(2))))), 6)

    @staticmethod
    def _frequency_entropy(
        counts: Counter[int],
        min_number: int,
        max_number: int,
    ) -> dict[str, object]:
        total = sum(counts.values())
        if total <= 0:
            return {"value": 0, "max": 0, "normalized": 0}
        entropy = 0.0
        for number in range(min_number, max_number + 1):
            probability = counts[number] / total
            if probability > 0:
                entropy -= probability * log2(probability)
        max_entropy = log2(max_number - min_number + 1)
        return {
            "value": round(entropy, 4),
            "max": round(max_entropy, 4),
            "normalized": round(entropy / max_entropy, 4) if max_entropy else 0,
        }

    @staticmethod
    def _build_sequence_summary(values: list[int]) -> dict[str, object]:
        if not values:
            return {"min": None, "max": None, "average": None, "stddev": None}
        average = mean(values)
        variance = mean([(value - average) ** 2 for value in values])
        return {
            "min": min(values),
            "max": max(values),
            "average": round(average, 2),
            "stddev": round(sqrt(variance), 4),
        }

    @staticmethod
    def _lag_one_correlation(values: list[int]) -> float | None:
        if len(values) < 3:
            return None
        left = values[:-1]
        right = values[1:]
        left_mean = mean(left)
        right_mean = mean(right)
        numerator = sum(
            (left_value - left_mean) * (right_value - right_mean)
            for left_value, right_value in zip(left, right, strict=True)
        )
        left_denominator = sqrt(sum((value - left_mean) ** 2 for value in left))
        right_denominator = sqrt(sum((value - right_mean) ** 2 for value in right))
        if left_denominator == 0 or right_denominator == 0:
            return None
        return round(numerator / (left_denominator * right_denominator), 4)

    @staticmethod
    def _build_gap_summary(rows: list[list[int]]) -> dict[str, object]:
        gaps: list[int] = []
        for row in rows:
            sorted_row = sorted(row)
            gaps.extend(
                sorted_row[index + 1] - sorted_row[index]
                for index in range(len(sorted_row) - 1)
            )
        return {
            **LotteryService._build_sequence_summary(gaps),
            "distribution": LotteryService._summarize_distribution(
                [str(gap) for gap in gaps]
            )[:12],
        }

    @staticmethod
    def _build_co_occurrence_nodes(
        *,
        draws: list[dict[str, object]],
        area: str,
    ) -> list[dict[str, object]]:
        if area == "back":
            number_ranges = [("back", range(1, 13))]
        elif area == "cross":
            number_ranges = [("front", range(1, 36)), ("back", range(1, 13))]
        else:
            number_ranges = [("front", range(1, 36))]
        nodes: list[dict[str, object]] = []
        for node_area, numbers in number_ranges:
            key = "front_numbers" if node_area == "front" else "back_numbers"
            counts = Counter(number for draw in draws for number in draw[key])
            nodes.extend(
                {
                    "id": f"{node_area}-{number}",
                    "area": node_area,
                    "number": number,
                    "count": counts[number],
                }
                for number in numbers
            )
        return sorted(nodes, key=lambda item: (-int(item["count"]), str(item["id"])))

    @staticmethod
    def _build_co_occurrence_edges(
        *,
        draws: list[dict[str, object]],
        area: str,
    ) -> list[dict[str, object]]:
        counts: Counter[tuple[str, str]] = Counter()
        sample_size = len(draws)
        for draw in draws:
            front_numbers = sorted(list(draw["front_numbers"]))
            back_numbers = sorted(list(draw["back_numbers"]))
            if area == "front":
                pairs = [
                    (f"front-{left}", f"front-{right}")
                    for left, right in combinations(front_numbers, 2)
                ]
            elif area == "back":
                pairs = [
                    (f"back-{left}", f"back-{right}")
                    for left, right in combinations(back_numbers, 2)
                ]
            else:
                pairs = [
                    (f"front-{front}", f"back-{back}")
                    for front in front_numbers
                    for back in back_numbers
                ]
            counts.update(pairs)

        expected_probability = LotteryService._co_occurrence_expected_probability(area)
        expected = sample_size * expected_probability
        variance = sample_size * expected_probability * (1 - expected_probability)
        stddev = sqrt(variance) if variance > 0 else 0
        edges: list[dict[str, object]] = []
        for (source, target), count in counts.items():
            lift = count / expected if expected else 0
            z_score = (count - expected) / stddev if stddev else 0
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "count": count,
                    "expected": round(expected, 4),
                    "lift": round(lift, 4),
                    "z_score": round(z_score, 4),
                }
            )
        return edges

    @staticmethod
    def _co_occurrence_expected_probability(area: str) -> float:
        if area == "front":
            return 5 * 4 / (35 * 34)
        if area == "back":
            return 2 * 1 / (12 * 11)
        return (5 / 35) * (2 / 12)

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
        raw_metadata = LotteryService._parse_sync_run_metadata(run.raw_metadata_json)
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
            "details": raw_metadata.get("details", []),
        }

    @staticmethod
    def _parse_sync_run_metadata(raw_metadata_json: str | None) -> dict[str, object]:
        if not raw_metadata_json:
            return {}
        try:
            metadata = json.loads(raw_metadata_json)
        except json.JSONDecodeError:
            return {}
        return metadata if isinstance(metadata, dict) else {}

    @staticmethod
    def _serialize_saved_combination(
        combination: LotterySavedCombinationModel,
    ) -> dict[str, object]:
        return {
            "id": combination.id,
            "game_code": combination.game_code,
            "label": combination.label,
            "source": combination.source,
            "front_numbers": json.loads(combination.front_numbers_json),
            "back_numbers": json.loads(combination.back_numbers_json),
            "favorite": combination.favorite,
            "note": combination.note,
            "created_at": combination.created_at.isoformat(),
            "updated_at": combination.updated_at.isoformat(),
        }
