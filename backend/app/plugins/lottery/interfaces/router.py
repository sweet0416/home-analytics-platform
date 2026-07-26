from datetime import datetime
from threading import Lock
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.core.config.settings import get_settings
from app.core.database.session import SessionLocal, get_db
from app.plugins.lottery.application.notification import DltNotificationService, MANUAL_TRIGGER
from app.plugins.lottery.application.replay_service import LotteryReplayService
from app.plugins.lottery.application.services import LotteryService
from app.plugins.lottery.domain.constants import DLT_DISCLAIMER
from app.plugins.lottery.domain.sync import DrawSyncCommand
from app.plugins.lottery.interfaces.schemas import (
    DisclaimerRead,
    LotteryBackfillJobRead,
    LotteryBackfillRequest,
    LotteryBackfillRunRead,
    LotteryBacktestAnalysisRead,
    LotteryBacktestRequest,
    LotteryBasicStatisticsRead,
    LotteryCoOccurrenceRead,
    LotteryCombinationCoverageRead,
    LotteryCoverageRequest,
    LotteryDecayAnalysisRead,
    LotteryDataStageReportRead,
    LotteryDataStageRepairRead,
    LotteryDantuoAnalysisRead,
    LotteryDantuoRequest,
    LotteryDrawCoverageRead,
    LotteryDrawPageRead,
    LotteryDrawRead,
    LotteryNumberOmissionDetailRead,
    LotteryOmissionStatisticsRead,
    LotteryRandomnessDiagnosticsRead,
    LotteryRecommendationRead,
    LotteryReplayContextRead,
    LotteryReplayRequest,
    LotteryReplayRunDetailRead,
    LotteryReplayRunRead,
    LotteryReplayRunSummaryRead,
    LotteryRuleRead,
    LotterySavedCombinationCreate,
    LotterySavedCombinationRead,
    LotterySavedCombinationUpdate,
    LotterySamePeriodAnalysisRead,
    LotterySensitivityRead,
    LotterySensitivityRequest,
    LotterySensitivityJobRead,
    LotterySimulationRead,
    LotterySyncRequest,
    LotterySyncRunPageRead,
    LotterySyncRunRead,
    LotterySyncStatusRead,
)
from app.plugins.lottery.jobs.scheduler import get_lottery_scheduler_status
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode
from app.shared.responses.schemas import ApiResponse, ok

router = APIRouter(prefix="/dlt")

_SENSITIVITY_JOB_LIMIT = 20
_SENSITIVITY_JOBS: dict[str, dict[str, object]] = {}
_SENSITIVITY_JOBS_LOCK = Lock()


def _prune_sensitivity_jobs() -> None:
    removable_job_ids = [
        job_id
        for job_id, job in _SENSITIVITY_JOBS.items()
        if job.get("status") in {"success", "failed"}
    ]
    overflow = len(_SENSITIVITY_JOBS) - _SENSITIVITY_JOB_LIMIT
    for job_id in removable_job_ids[: max(0, overflow)]:
        _SENSITIVITY_JOBS.pop(job_id, None)


def _update_sensitivity_job(job_id: str, **updates: object) -> None:
    with _SENSITIVITY_JOBS_LOCK:
        current = _SENSITIVITY_JOBS.get(job_id, {})
        current.update(updates)
        _SENSITIVITY_JOBS[job_id] = current


def _run_backfill_task(payload: LotteryBackfillRequest) -> None:
    db = SessionLocal()
    try:
        LotteryService(db).backfill_draws(
            start_page=payload.start_page,
            page_count=payload.page_count,
            page_size=payload.page_size,
            force=payload.force,
        )
    finally:
        db.close()


def _run_sensitivity_task(job_id: str, payload: LotterySensitivityRequest) -> None:
    started_at = datetime.now()
    _update_sensitivity_job(
        job_id,
        status="running",
        message="参数敏感度分析正在后台运行。",
        started_at=started_at.isoformat(),
    )
    db = SessionLocal()
    try:
        result = LotteryReplayService(db).analyze_parameter_sensitivity(
            target_issue_no=payload.target_issue_no,
            target_count=payload.target_count,
            sets=payload.sets,
            same_period_count=payload.same_period_count,
            sample_windows=payload.sample_windows,
            weight_profiles=[item.model_dump() for item in payload.weight_profiles],
            baseline_simulations=payload.baseline_simulations,
            seed=payload.seed,
        )
        finished_at = datetime.now()
        _update_sensitivity_job(
            job_id,
            status="success",
            message="参数敏感度分析完成。",
            finished_at=finished_at.isoformat(),
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
            result=result,
        )
    except AppError as exc:
        finished_at = datetime.now()
        _update_sensitivity_job(
            job_id,
            status="failed",
            message=exc.message,
            finished_at=finished_at.isoformat(),
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
            error_code=str(exc.code),
            error_message=exc.message,
        )
    except Exception as exc:  # noqa: BLE001
        finished_at = datetime.now()
        _update_sensitivity_job(
            job_id,
            status="failed",
            message="参数敏感度分析失败。",
            finished_at=finished_at.isoformat(),
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
            error_code=ErrorCode.internal_error.value,
            error_message=str(exc),
        )
    finally:
        db.close()


@router.get("/rules/current", response_model=ApiResponse[LotteryRuleRead])
def get_current_rule(db: Session = Depends(get_db)) -> ApiResponse[LotteryRuleRead]:
    service = LotteryService(db)
    return ok(service.get_current_rule())


@router.get("/draws", response_model=ApiResponse[LotteryDrawPageRead])
def list_draws(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryDrawPageRead]:
    service = LotteryService(db)
    return ok(service.list_draws(page=page, page_size=page_size))


@router.get("/draws/latest", response_model=ApiResponse[LotteryDrawRead])
def get_latest_draw(db: Session = Depends(get_db)) -> ApiResponse[LotteryDrawRead]:
    service = LotteryService(db)
    return ok(service.get_latest_draw())


@router.get("/draws/coverage", response_model=ApiResponse[LotteryDrawCoverageRead])
def get_draw_coverage(db: Session = Depends(get_db)) -> ApiResponse[LotteryDrawCoverageRead]:
    service = LotteryService(db)
    return ok(service.get_draw_coverage())


@router.get("/data/stages", response_model=ApiResponse[LotteryDataStageReportRead])
def get_data_stage_report(
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryDataStageReportRead]:
    service = LotteryService(db)
    return ok(service.get_data_stage_report())


@router.post(
    "/data/stages/repair-rule-bindings",
    response_model=ApiResponse[LotteryDataStageRepairRead],
)
def repair_data_stage_bindings(
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryDataStageRepairRead]:
    service = LotteryService(db)
    return ok(service.repair_data_stage_bindings())


@router.get("/draws/{issue_no}", response_model=ApiResponse[LotteryDrawRead])
def get_draw_by_issue(issue_no: str, db: Session = Depends(get_db)) -> ApiResponse[LotteryDrawRead]:
    service = LotteryService(db)
    return ok(service.get_draw_by_issue(issue_no))


@router.get("/combinations", response_model=ApiResponse[list[LotterySavedCombinationRead]])
def list_saved_combinations(
    db: Session = Depends(get_db),
) -> ApiResponse[list[LotterySavedCombinationRead]]:
    service = LotteryService(db)
    return ok(service.list_saved_combinations())


@router.post("/combinations", response_model=ApiResponse[LotterySavedCombinationRead])
def save_combination(
    payload: LotterySavedCombinationCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[LotterySavedCombinationRead]:
    service = LotteryService(db)
    return ok(
        service.save_combination(
            label=payload.label,
            source=payload.source,
            front_numbers=payload.front_numbers,
            back_numbers=payload.back_numbers,
            favorite=payload.favorite,
            note=payload.note,
        )
    )


@router.patch(
    "/combinations/{combination_id}",
    response_model=ApiResponse[LotterySavedCombinationRead],
)
def update_saved_combination(
    combination_id: int,
    payload: LotterySavedCombinationUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[LotterySavedCombinationRead]:
    service = LotteryService(db)
    return ok(
        service.update_saved_combination(
            combination_id,
            label=payload.label,
            source=payload.source,
            favorite=payload.favorite,
            note=payload.note,
        )
    )


@router.delete("/combinations/{combination_id}", response_model=ApiResponse[dict[str, object]])
def delete_saved_combination(
    combination_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, object]]:
    service = LotteryService(db)
    return ok(service.delete_saved_combination(combination_id))


@router.get("/statistics/basic", response_model=ApiResponse[LotteryBasicStatisticsRead])
def get_basic_statistics(
    limit: int = Query(default=100, ge=10, le=500),
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryBasicStatisticsRead]:
    service = LotteryService(db)
    return ok(service.get_basic_statistics(limit=limit))


@router.get("/statistics/omissions", response_model=ApiResponse[LotteryOmissionStatisticsRead])
def get_omission_statistics(
    limit: int = Query(default=100, ge=10, le=500),
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryOmissionStatisticsRead]:
    service = LotteryService(db)
    return ok(service.get_omission_statistics(limit=limit))


@router.get("/statistics/randomness", response_model=ApiResponse[LotteryRandomnessDiagnosticsRead])
def get_randomness_diagnostics(
    limit: int = Query(default=500, ge=50, le=2000),
    stage_code: str | None = Query(default=None, min_length=1, max_length=64),
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryRandomnessDiagnosticsRead]:
    service = LotteryService(db)
    return ok(service.get_randomness_diagnostics(limit=limit, stage_code=stage_code))


@router.get(
    "/numbers/{area}/{number}/omission",
    response_model=ApiResponse[LotteryNumberOmissionDetailRead],
)
def get_number_omission_detail(
    area: str,
    number: int,
    limit: int = Query(default=200, ge=10, le=500),
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryNumberOmissionDetailRead]:
    service = LotteryService(db)
    return ok(service.get_number_omission_detail(area=area, number=number, limit=limit))


@router.get("/analysis/same-period", response_model=ApiResponse[LotterySamePeriodAnalysisRead])
def get_same_period_analysis(
    issue_no: str | None = Query(default=None, min_length=3, max_length=16),
    count: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> ApiResponse[LotterySamePeriodAnalysisRead]:
    service = LotteryService(db)
    return ok(service.get_same_period_analysis(issue_no=issue_no, count=count))


@router.get("/analysis/co-occurrence", response_model=ApiResponse[LotteryCoOccurrenceRead])
def get_co_occurrence_analysis(
    area: str = Query(default="front", pattern="^(front|back|cross)$"),
    limit: int = Query(default=500, ge=50, le=2000),
    top: int = Query(default=30, ge=5, le=100),
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryCoOccurrenceRead]:
    service = LotteryService(db)
    return ok(service.get_co_occurrence_analysis(area=area, limit=limit, top=top))


@router.get("/analysis/decay", response_model=ApiResponse[LotteryDecayAnalysisRead])
def get_decay_analysis(
    limit: int = Query(default=500, ge=50, le=2000),
    half_life: int = Query(default=50, ge=5, le=500),
    top: int = Query(default=10, ge=5, le=20),
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryDecayAnalysisRead]:
    service = LotteryService(db)
    return ok(service.get_decay_analysis(limit=limit, half_life=half_life, top=top))


@router.get("/analysis/recommendations", response_model=ApiResponse[LotteryRecommendationRead])
def get_recommendations(
    issue_no: str | None = Query(default=None, min_length=3, max_length=16),
    sets: int = Query(default=5, ge=1, le=12),
    same_period_count: int = Query(default=10, ge=1, le=20),
    sample_limit: int = Query(default=200, ge=50, le=500),
    same_period_weight: float = Query(default=45, ge=0, le=100),
    frequency_weight: float = Query(default=25, ge=0, le=100),
    missing_weight: float = Query(default=20, ge=0, le=100),
    structure_weight: float = Query(default=10, ge=0, le=100),
    co_occurrence_weight: float = Query(default=15, ge=0, le=100),
    coverage_weight: float = Query(default=8, ge=0, le=100),
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryRecommendationRead]:
    service = LotteryService(db)
    return ok(
        service.get_recommendations(
            issue_no=issue_no,
            sets=sets,
            same_period_count=same_period_count,
            sample_limit=sample_limit,
            same_period_weight=same_period_weight,
            frequency_weight=frequency_weight,
            missing_weight=missing_weight,
            structure_weight=structure_weight,
            co_occurrence_weight=co_occurrence_weight,
            coverage_weight=coverage_weight,
        )
    )


@router.get("/analysis/simulation", response_model=ApiResponse[LotterySimulationRead])
def simulate_numbers(
    simulations: int = Query(default=10000, ge=100, le=50000),
    sets: int = Query(default=5, ge=1, le=20),
    seed: int | None = Query(default=None, ge=0, le=2147483647),
    db: Session = Depends(get_db),
) -> ApiResponse[LotterySimulationRead]:
    service = LotteryService(db)
    return ok(service.simulate_numbers(simulations=simulations, sets=sets, seed=seed))


@router.post("/analysis/coverage", response_model=ApiResponse[LotteryCombinationCoverageRead])
def analyze_combination_coverage(
    payload: LotteryCoverageRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryCombinationCoverageRead]:
    service = LotteryService(db)
    return ok(
        service.analyze_combination_coverage(
            combinations=[
                combination.model_dump() for combination in payload.combinations
            ],
        )
    )


@router.post("/analysis/dantuo", response_model=ApiResponse[LotteryDantuoAnalysisRead])
def analyze_dantuo(
    payload: LotteryDantuoRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryDantuoAnalysisRead]:
    service = LotteryService(db)
    return ok(
        service.analyze_dantuo(
            front_dan=payload.front_dan,
            front_tuo=payload.front_tuo,
            front_kill=payload.front_kill,
            back_dan=payload.back_dan,
            back_tuo=payload.back_tuo,
            back_kill=payload.back_kill,
            addon=payload.addon,
            preview_limit=payload.preview_limit,
        )
    )


@router.post("/analysis/backtest", response_model=ApiResponse[LotteryBacktestAnalysisRead])
def backtest_numbers(
    payload: LotteryBacktestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryBacktestAnalysisRead]:
    service = LotteryService(db)
    return ok(
        service.backtest_numbers(
            front_numbers=payload.front_numbers,
            back_numbers=payload.back_numbers,
            addon=payload.addon,
            hit_limit=payload.hit_limit,
        )
    )


@router.get(
    "/analysis/replay/context",
    response_model=ApiResponse[LotteryReplayContextRead],
)
def get_replay_context(
    target_issue_no: str = Query(min_length=3, max_length=16),
    sample_limit: int = Query(default=500, ge=20, le=2000),
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryReplayContextRead]:
    service = LotteryReplayService(db)
    return ok(service.get_replay_context(target_issue_no=target_issue_no, sample_limit=sample_limit))


@router.get(
    "/analysis/replay/runs",
    response_model=ApiResponse[list[LotteryReplayRunSummaryRead]],
)
def list_replay_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ApiResponse[list[LotteryReplayRunSummaryRead]]:
    service = LotteryReplayService(db)
    return ok(service.list_replay_runs(limit=limit))


@router.get(
    "/analysis/replay/runs/{run_id}",
    response_model=ApiResponse[LotteryReplayRunDetailRead],
)
def get_replay_run(
    run_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryReplayRunDetailRead]:
    service = LotteryReplayService(db)
    return ok(service.get_replay_run(run_id))


@router.post("/analysis/replay", response_model=ApiResponse[LotteryReplayRunRead])
def run_replay(
    payload: LotteryReplayRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryReplayRunRead]:
    service = LotteryReplayService(db)
    return ok(
        service.run_replay(
            target_issue_no=payload.target_issue_no,
            sets=payload.sets,
            sample_limit=payload.sample_limit,
            same_period_count=payload.same_period_count,
            baseline_simulations=payload.baseline_simulations,
            seed=payload.seed,
            same_period_weight=payload.strategy.same_period_weight,
            frequency_weight=payload.strategy.frequency_weight,
            missing_weight=payload.strategy.missing_weight,
            structure_weight=payload.strategy.structure_weight,
            coverage_weight=payload.strategy.coverage_weight,
        )
    )


@router.post(
    "/analysis/replay/sensitivity",
    response_model=ApiResponse[LotterySensitivityRead],
)
def analyze_replay_sensitivity(
    payload: LotterySensitivityRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[LotterySensitivityRead]:
    service = LotteryReplayService(db)
    return ok(
        service.analyze_parameter_sensitivity(
            target_issue_no=payload.target_issue_no,
            target_count=payload.target_count,
            sets=payload.sets,
            same_period_count=payload.same_period_count,
            sample_windows=payload.sample_windows,
            weight_profiles=[profile.model_dump() for profile in payload.weight_profiles] or None,
            baseline_simulations=payload.baseline_simulations,
            seed=payload.seed,
        )
    )


@router.post(
    "/analysis/replay/sensitivity/start",
    response_model=ApiResponse[LotterySensitivityJobRead],
)
def start_replay_sensitivity(
    payload: LotterySensitivityRequest,
    background_tasks: BackgroundTasks,
) -> ApiResponse[LotterySensitivityJobRead]:
    job_id = uuid4().hex
    created_at = datetime.now().isoformat()
    job = {
        "job_id": job_id,
        "status": "queued",
        "message": "参数敏感度分析已排队，页面会自动刷新进度。",
        "started_at": created_at,
        "finished_at": None,
        "duration_ms": None,
        "payload": payload,
        "result": None,
        "error_code": None,
        "error_message": None,
    }
    with _SENSITIVITY_JOBS_LOCK:
        _SENSITIVITY_JOBS[job_id] = job
        _prune_sensitivity_jobs()
    background_tasks.add_task(_run_sensitivity_task, job_id, payload)
    return ok(job)


@router.get(
    "/analysis/replay/sensitivity/jobs/{job_id}",
    response_model=ApiResponse[LotterySensitivityJobRead],
)
def get_replay_sensitivity_job(job_id: str) -> ApiResponse[LotterySensitivityJobRead]:
    with _SENSITIVITY_JOBS_LOCK:
        job = _SENSITIVITY_JOBS.get(job_id)
    if job is None:
        raise AppError(
            code=ErrorCode.not_found,
            message="Sensitivity analysis job was not found.",
            status_code=404,
        )
    return ok(job)


@router.post("/sync", response_model=ApiResponse[LotterySyncRunRead])
def sync_draws(
    payload: LotterySyncRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[LotterySyncRunRead]:
    service = LotteryService(db)
    command = DrawSyncCommand(
        sync_type=payload.sync_type,
        page=payload.page,
        page_size=payload.page_size,
        force=payload.force,
    )
    notifier = DltNotificationService(get_settings())
    try:
        result = service.sync_draws(command)
    except Exception as exc:
        if payload.sync_type == "manual":
            notifier.notify_sync_exception(trigger_type=MANUAL_TRIGGER, exc=exc)
        raise

    if payload.sync_type == "manual":
        notifier.notify_sync_result(
            service=service,
            result=result,
            trigger_type=MANUAL_TRIGGER,
        )
    return ok(result)


@router.post("/sync/backfill", response_model=ApiResponse[LotteryBackfillRunRead])
def backfill_draws(
    payload: LotteryBackfillRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryBackfillRunRead]:
    service = LotteryService(db)
    return ok(
        service.backfill_draws(
            start_page=payload.start_page,
            page_count=payload.page_count,
            page_size=payload.page_size,
            force=payload.force,
        )
    )


@router.post("/sync/backfill/start", response_model=ApiResponse[LotteryBackfillJobRead])
def start_backfill_draws(
    payload: LotteryBackfillRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryBackfillJobRead]:
    service = LotteryService(db)
    if service.repository.has_running_sync():
        raise AppError(
            code=ErrorCode.lottery_sync_already_running,
            message="A lottery sync or backfill task is already running.",
            status_code=409,
        )
    background_tasks.add_task(_run_backfill_task, payload)
    return ok(
        {
            "status": "queued",
            "message": "\u5386\u53f2\u56de\u586b\u5df2\u5728\u540e\u53f0\u5f00\u59cb\uff0c\u9875\u9762\u4f1a\u81ea\u52a8\u5237\u65b0\u8fdb\u5ea6\u3002",
            "start_page": payload.start_page,
            "page_count": payload.page_count,
            "page_size": payload.page_size,
            "force": payload.force,
        }
    )


@router.get("/sync/latest", response_model=ApiResponse[LotterySyncRunRead])
def get_latest_sync_run(db: Session = Depends(get_db)) -> ApiResponse[LotterySyncRunRead]:
    service = LotteryService(db)
    return ok(service.get_latest_sync_run())


@router.get("/sync/status", response_model=ApiResponse[LotterySyncStatusRead])
def get_sync_status(db: Session = Depends(get_db)) -> ApiResponse[LotterySyncStatusRead]:
    service = LotteryService(db)
    latest_run: dict[str, object] | None
    try:
        latest_run = service.get_latest_sync_run()
    except AppError as exc:
        if exc.code is not ErrorCode.lottery_sync_run_not_found:
            raise
        latest_run = None

    return ok({**get_lottery_scheduler_status(), "latest_run": latest_run})


@router.get("/sync/runs", response_model=ApiResponse[LotterySyncRunPageRead])
def list_sync_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None, pattern="^(running|success|partial_success|failed)$"),
    sync_type: str | None = Query(default=None, pattern="^(manual|scheduled|backfill)$"),
    db: Session = Depends(get_db),
) -> ApiResponse[LotterySyncRunPageRead]:
    service = LotteryService(db)
    return ok(
        service.list_sync_runs(
            page=page,
            page_size=page_size,
            status=status,
            sync_type=sync_type,
        )
    )


@router.get("/disclaimer", response_model=ApiResponse[DisclaimerRead])
def get_disclaimer() -> ApiResponse[DisclaimerRead]:
    return ok({"disclaimer": DLT_DISCLAIMER})
