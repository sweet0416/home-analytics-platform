from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.config.settings import Settings
from app.plugins.fund.application.ai_summary import (
    FundAiSummaryProviderError,
    FundDailyAiSummaryService,
)
from app.plugins.fund.infrastructure.ai_summary_openai import FundAiSummaryOpenAIProvider
from app.plugins.fund.infrastructure.ai_summary_webhook import FundAiSummaryWebhookProvider
from app.shared.exceptions.base import AppError


def _payload() -> SimpleNamespace:
    return SimpleNamespace(
        report_date=date(2026, 8, 2),
        model_dump=lambda mode: {
            "contract_version": "fund-daily-ai-input.v1",
            "report_date": "2026-08-02",
        },
        model_dump_json=lambda: '{"contract_version":"fund-daily-ai-input.v1"}',
    )


def test_ai_summary_is_disabled_by_default() -> None:
    settings = Settings(_env_file=None)
    provider = Mock()
    service = FundDailyAiSummaryService(settings=settings, provider=provider)

    status = service.get_status()
    assert status.enabled is False
    assert status.configured is False
    assert status.target == "未配置"

    with pytest.raises(AppError) as error:
        service.generate(_payload())

    assert error.value.status_code == 503
    provider.summarize.assert_not_called()


def test_webhook_provider_sends_versioned_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        _env_file=None,
        fund_ai_summary_enabled=True,
        fund_ai_summary_webhook_url="https://ai.example.test/hap-summary",
        fund_ai_summary_bearer_token="secret-token",
        fund_ai_summary_timeout_seconds=12,
    )
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"summary": "  今日持仓估值保持稳定。  "}
    post = Mock(return_value=response)
    monkeypatch.setattr("app.plugins.fund.infrastructure.ai_summary_webhook.requests.post", post)

    summary = FundAiSummaryWebhookProvider(settings).summarize(_payload())

    assert summary == "今日持仓估值保持稳定。"
    request = post.call_args
    assert request.args == ("https://ai.example.test/hap-summary",)
    assert request.kwargs["timeout"] == 12
    assert request.kwargs["headers"]["Authorization"] == "Bearer secret-token"
    assert request.kwargs["headers"]["X-HAP-Contract"] == "hap-ai-webhook.v1"
    assert request.kwargs["json"]["schema_version"] == "hap-ai-webhook.v1"
    assert request.kwargs["json"]["task"] == "fund_daily_summary"
    assert request.kwargs["json"]["input"]["contract_version"] == (
        "fund-daily-ai-input.v1"
    )


def test_webhook_provider_rejects_invalid_response(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        _env_file=None,
        fund_ai_summary_enabled=True,
        fund_ai_summary_webhook_url="https://ai.example.test/hap-summary",
    )
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"text": "missing summary field"}
    monkeypatch.setattr(
        "app.plugins.fund.infrastructure.ai_summary_webhook.requests.post",
        Mock(return_value=response),
    )

    with pytest.raises(FundAiSummaryProviderError, match="non-empty string field"):
        FundAiSummaryWebhookProvider(settings).summarize(_payload())


def test_openai_compatible_provider_sends_chat_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        fund_ai_summary_enabled=True,
        fund_ai_summary_provider="openai_compatible",
        fund_ai_summary_api_url="https://api.example.test/v1/chat/completions",
        fund_ai_summary_api_key="secret-token",
        fund_ai_summary_model="summary-model",
        fund_ai_summary_timeout_seconds=17,
    )
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "choices": [{"message": {"content": "  今日风险可控。 "}}],
    }
    post = Mock(return_value=response)
    monkeypatch.setattr(
        "app.plugins.fund.infrastructure.ai_summary_openai.requests.post",
        post,
    )

    summary = FundAiSummaryOpenAIProvider(settings).summarize(_payload())

    assert summary == "今日风险可控。"
    request = post.call_args
    assert request.args == ("https://api.example.test/v1/chat/completions",)
    assert request.kwargs["timeout"] == 17
    assert request.kwargs["headers"]["Authorization"] == "Bearer secret-token"
    assert request.kwargs["json"]["model"] == "summary-model"
    assert request.kwargs["json"]["messages"][-1]["content"] == (
        '{"contract_version":"fund-daily-ai-input.v1"}'
    )


def test_openai_compatible_status_requires_all_credentials() -> None:
    settings = Settings(
        _env_file=None,
        fund_ai_summary_enabled=True,
        fund_ai_summary_provider="openai_compatible",
        fund_ai_summary_api_url="https://api.example.test/v1/chat/completions",
        fund_ai_summary_model="summary-model",
    )

    status = FundDailyAiSummaryService(settings=settings, provider=Mock()).get_status()

    assert status.provider == "openai_compatible"
    assert status.enabled is True
    assert status.configured is False


def test_ai_summary_service_wraps_provider_result() -> None:
    settings = Settings(
        _env_file=None,
        fund_ai_summary_enabled=True,
        fund_ai_summary_webhook_url="https://ai.example.test/hap-summary",
    )
    provider = Mock()
    provider.summarize.return_value = "今日无明显异常。"

    result = FundDailyAiSummaryService(settings=settings, provider=provider).generate(
        _payload()
    )

    assert result.contract_version == "fund-daily-ai-summary.v1"
    assert result.report_date == date(2026, 8, 2)
    assert result.summary == "今日无明显异常。"
    assert "不构成投资建议" in result.disclaimer
