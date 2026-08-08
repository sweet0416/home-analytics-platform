from typing import Any

import requests

from app.core.config.settings import Settings
from app.plugins.fund.application.ai_summary import (
    FundAiSummaryProviderError,
    FundAiSummaryUsage,
)
from app.plugins.fund.interfaces.schemas import FundDailyAiInputRead


class FundAiSummaryOpenAIProvider:
    """Call an OpenAI-compatible chat-completions endpoint."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.usage = FundAiSummaryUsage()

    def summarize(self, payload: FundDailyAiInputRead) -> str:
        url = self._settings.fund_ai_summary_api_url.strip()
        headers = {
            "Authorization": f"Bearer {self._settings.fund_ai_summary_api_key.strip()}",
            "Content-Type": "application/json",
            "X-HAP-Contract": "hap-ai-openai-compatible.v1",
        }
        body = {
            "model": self._settings.fund_ai_summary_model.strip(),
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You summarize HAP fund daily reports. Use only supplied facts. "
                        "Do not predict prices or returns, and do not give investment advice. "
                        "Write a concise Chinese summary with risks and data limitations."
                    ),
                },
                {
                    "role": "user",
                    "content": payload.model_dump_json(),
                },
            ],
        }
        try:
            response = requests.post(
                url,
                headers=headers,
                json=body,
                timeout=self._settings.fund_ai_summary_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FundAiSummaryProviderError(str(exc)) from exc

        response_payload = self._safe_json(response)
        self.usage = self._extract_usage(response_payload)
        summary = self._extract_summary(response_payload)
        if not summary:
            raise FundAiSummaryProviderError(
                "OpenAI-compatible response has no non-empty choices[0].message.content."
            )
        return summary

    @staticmethod
    def _extract_usage(payload: dict[str, Any]) -> FundAiSummaryUsage:
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return FundAiSummaryUsage()
        cost = usage.get("cost", payload.get("cost"))
        return FundAiSummaryUsage(
            input_tokens=FundAiSummaryOpenAIProvider._as_int(
                usage.get("prompt_tokens", usage.get("input_tokens"))
            ),
            output_tokens=FundAiSummaryOpenAIProvider._as_int(
                usage.get("completion_tokens", usage.get("output_tokens"))
            ),
            cost=FundAiSummaryOpenAIProvider._as_float(cost),
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
            raise FundAiSummaryProviderError("AI response is not valid JSON.") from exc
        if not isinstance(payload, dict):
            raise FundAiSummaryProviderError("AI response must be a JSON object.")
        return payload

    @staticmethod
    def _extract_summary(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""
        message = first.get("message")
        if not isinstance(message, dict):
            return ""
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            ]
            return "".join(parts).strip()
        return ""
