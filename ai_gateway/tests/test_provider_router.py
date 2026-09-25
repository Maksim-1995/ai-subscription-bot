from unittest.mock import AsyncMock

import pytest

from app.schemas.provider import ProviderResult
from app.services.exceptions import (
    ProviderUnavailableError,
)
from app.services.providers import router


@pytest.mark.asyncio
async def test_primary_provider_success(monkeypatch):
    openai_result = ProviderResult(
        provider='openai',
        model='gpt-5.6-luna',
        text='OpenAI response',
        prompt_tokens=10,
        completion_tokens=5,
        stop_reason='completed',
    )

    openai_mock = AsyncMock(
        return_value=openai_result,
    )

    deepseek_mock = AsyncMock()

    monkeypatch.setattr(
        router,
        'create_openai_completion',
        openai_mock,
    )

    monkeypatch.setattr(
        router,
        'create_deepseek_completion',
        deepseek_mock,
    )

    request = AsyncMock()

    result = await router.generate_completion(
        request,
    )

    assert result.result.provider == 'openai'
    assert result.fallback_used is False

    openai_mock.assert_awaited_once()
    deepseek_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_fallback_to_deepseek(monkeypatch):
    deepseek_result = ProviderResult(
        provider='deepseek',
        model='deepseek-flash',
        text='DeepSeek response',
        prompt_tokens=10,
        completion_tokens=5,
        stop_reason='stop',
    )

    openai_mock = AsyncMock(
        side_effect=ProviderUnavailableError,
    )

    deepseek_mock = AsyncMock(
        return_value=deepseek_result,
    )

    monkeypatch.setattr(
        router,
        'create_openai_completion',
        openai_mock,
    )

    monkeypatch.setattr(
        router,
        'create_deepseek_completion',
        deepseek_mock,
    )

    request = AsyncMock()

    result = await router.generate_completion(
        request,
    )

    assert result.result.provider == 'deepseek'
    assert result.fallback_used is True

    openai_mock.assert_awaited_once()
    deepseek_mock.assert_awaited_once()
