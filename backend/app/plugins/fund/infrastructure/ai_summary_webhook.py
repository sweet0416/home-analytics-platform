from typing import Any

import requests

from app.core.config.settings import Settings
from app.plugins.fund.application.ai_summary import (
    FundAiSummaryProviderError,
    FundAiSummaryUsage,
)
from app.plugins.fund.interfaces.schemas import FundDailyAiInputRead


class FundAiSummaryWebhookProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.usage = FundAiSummaryUsage()

    def summarize(self, payload: FundDailyAiInputRead) -> str:
        url = self._settings.fund_ai_summary_webhook_url.strip()
        headers = {
            "Content-Type": "application/json",
            "X-HAP-Contract": "hap-ai-webhook.v1",
        }
        bearer_token = self._settings.fund_ai_summary_bearer_token.strip()
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        try:
            response = requests.post(
                url,
                headers=headers,
                json={
                    "schema_version": "hap-ai-webhook.v1",
                    "task": "fund_daily_summary",
                    "input": payload.model_dump(mode="json"),
                },
                timeout=self._settings.fund_ai_summary_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FundAiSummaryProviderError(str(exc)) from exc

        response_payload = self._safe_json(response)
        self.usage = self._extract_usage(response_payload)
        summary = response_payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise FundAiSummaryProviderError(
                "Webhook response must contain a non-empty string field named 'summary'."
            )
        return summary.strip()

    @staticmethod
    def _extract_usage(payload: dict[str, Any]) -> FundAiSummaryUsage:
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return FundAiSummaryUsage()
        return FundAiSummaryUsage(
            input_tokens=FundAiSummaryWebhookProvider._as_int(
                usage.get("input_tokens", usage.get("prompt_tokens"))
            ),
            output_tokens=FundAiSummaryWebhookProvider._as_int(
                usage.get("output_tokens", usage.get("completion_tokens"))
            ),
            cost=FundAiSummaryWebhookProvider._as_float(
                usage.get("cost", payload.get("cost"))
            ),
        )

    @staticmethod
    def _as_int(value: object) -> int | None:
        return int(value) if isinstance(value, int | float) else None

    @staticmethod
    def _as_float(value: object) -> float | None:
        return float(value) if isinstance(value, int | float) else None

    @staticmethod
    def _safe_json(response: requests.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise FundAiSummaryProviderError("Webhook response is not valid JSON.") from exc
        if not isinstance(payload, dict):
            raise FundAiSummaryProviderError("Webhook response must be a JSON object.")
        return payload
