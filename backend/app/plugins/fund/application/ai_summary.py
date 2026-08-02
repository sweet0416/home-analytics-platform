from datetime import datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from loguru import logger

from app.core.config.settings import Settings
from app.plugins.fund.interfaces.schemas import (
    FundDailyAiInputRead,
    FundDailyAiSummaryRead,
    FundDailyAiSummaryStatusRead,
)
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


class FundAiSummaryProviderError(RuntimeError):
    """Raised when the configured AI provider cannot return a valid summary."""


class FundAiSummaryProvider(Protocol):
    def summarize(self, payload: FundDailyAiInputRead) -> str: ...


class FundDailyAiSummaryService:
    def __init__(self, settings: Settings, provider: FundAiSummaryProvider) -> None:
        self._settings = settings
        self._provider = provider

    def get_status(self) -> FundDailyAiSummaryStatusRead:
        webhook_url = self._settings.fund_ai_summary_webhook_url.strip()
        return FundDailyAiSummaryStatusRead(
            provider="webhook",
            enabled=self._settings.fund_ai_summary_enabled,
            configured=bool(webhook_url),
            target=self._mask_url(webhook_url),
            input_contract="fund-daily-ai-input.v1",
            note=(
                "仅在手动生成摘要时发送结构化日报输入；默认关闭，"
                "不会自动上传持仓数据。"
            ),
        )

    def generate(self, payload: FundDailyAiInputRead) -> FundDailyAiSummaryRead:
        status = self.get_status()
        if not status.enabled:
            raise AppError(
                ErrorCode.fund_ai_summary_unavailable,
                "Fund AI summary is disabled.",
                status_code=503,
            )
        if not status.configured:
            raise AppError(
                ErrorCode.fund_ai_summary_unavailable,
                "Fund AI summary webhook is not configured.",
                status_code=503,
            )

        try:
            summary = self._provider.summarize(payload).strip()
        except FundAiSummaryProviderError as exc:
            logger.warning("Fund AI summary provider failed: {}", exc)
            raise AppError(
                ErrorCode.fund_ai_summary_unavailable,
                "Fund AI summary provider is unavailable.",
                status_code=502,
                details={"reason": str(exc)},
            ) from exc

        if not summary:
            raise AppError(
                ErrorCode.fund_ai_summary_unavailable,
                "Fund AI summary provider returned an empty summary.",
                status_code=502,
            )
        return FundDailyAiSummaryRead(
            contract_version="fund-daily-ai-summary.v1",
            generated_at=datetime.now(ZoneInfo("Asia/Shanghai")),
            report_date=payload.report_date,
            provider="webhook",
            source_contract="fund-daily-ai-input.v1",
            summary=summary,
            disclaimer="AI 摘要仅整理已提供的数据事实，不构成投资建议。",
        )

    @staticmethod
    def _mask_url(value: str) -> str:
        if not value:
            return "未配置"
        if len(value) <= 28:
            return "***"
        return f"{value[:18]}...{value[-8:]}"
