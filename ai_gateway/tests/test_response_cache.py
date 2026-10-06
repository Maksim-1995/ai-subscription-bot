import pytest

from unittest.mock import AsyncMock

from app.core.config import settings
from app.schemas.provider import ProviderResult
from app.schemas.chat import (
    ChatCompletionRequest,
    ChatMessage,
)
from app.services.response_cache import (
    build_response_cache_key,
    get_cached_completion,
    set_cached_completion,
)


def test_same_requests_have_same_cache_key():
    first = ChatCompletionRequest(
        model='gpt-5.6-luna',
        messages=[
            ChatMessage(
                role='user',
                content='Hello',
            ),
        ],
        temperature=1.0,
    )

    second = ChatCompletionRequest(
        model='gpt-5.6-luna',
        messages=[
            ChatMessage(
                role='user',
                content='Hello',
            ),
        ],
        temperature=1.0,
    )

    assert (
        build_response_cache_key(first)
        == build_response_cache_key(second)
    )


def test_different_messages_have_different_cache_keys():
    first = ChatCompletionRequest(
        model='gpt-5.6-luna',
        messages=[
            ChatMessage(
                role='user',
                content='Hello',
            ),
        ],
        temperature=1.0,
    )

    second = ChatCompletionRequest(
        model='gpt-5.6-luna',
        messages=[
            ChatMessage(
                role='user',
                content='Goodbye',
            ),
        ],
        temperature=1.0,
    )

    assert (
        build_response_cache_key(first)
        != build_response_cache_key(second)
    )


def test_different_temperature_has_different_cache_key():
    first = ChatCompletionRequest(
        model='gpt-5.6-luna',
        messages=[
            ChatMessage(
                role='user',
                content='Hello',
            ),
        ],
        temperature=0.2,
    )

    second = ChatCompletionRequest(
        model='gpt-5.6-luna',
        messages=[
            ChatMessage(
                role='user',
                content='Hello',
            ),
        ],
        temperature=1.0,
    )

    assert (
        build_response_cache_key(first)
        != build_response_cache_key(second)
    )


@pytest.mark.asyncio
async def test_get_cached_completion_returns_result(
    monkeypatch,
):
    request = ChatCompletionRequest(
        model='gpt-5.6-luna',
        messages=[
            ChatMessage(
                role='user',
                content='Hello',
            ),
        ],
        temperature=1.0,
    )

    cached_result = ProviderResult(
        provider='openai',
        model='gpt-5.6-luna',
        text='Cached answer',
        prompt_tokens=10,
        completion_tokens=5,
        stop_reason='completed',
    )

    redis_mock = AsyncMock()

    redis_mock.get.return_value = (
        cached_result.model_dump_json()
    )

    monkeypatch.setattr(
        'app.services.response_cache.redis_client',
        redis_mock,
    )

    result = await get_cached_completion(
        request,
    )

    assert result is not None

    assert result.provider == 'openai'
    assert result.model == 'gpt-5.6-luna'
    assert result.text == 'Cached answer'

    redis_mock.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_cached_completion_uses_ttl(
    monkeypatch,
):
    request = ChatCompletionRequest(
        model='gpt-5.6-luna',
        messages=[
            ChatMessage(
                role='user',
                content='Hello',
            ),
        ],
        temperature=1.0,
    )

    result = ProviderResult(
        provider='openai',
        model='gpt-5.6-luna',
        text='Hello!',
        prompt_tokens=10,
        completion_tokens=5,
        stop_reason='completed',
    )

    redis_mock = AsyncMock()

    monkeypatch.setattr(
        'app.services.response_cache.redis_client',
        redis_mock,
    )

    await set_cached_completion(
        request,
        result,
    )

    redis_mock.set.assert_awaited_once()

    call = redis_mock.set.await_args

    cache_key = call.args[0]
    cached_value = call.args[1]

    assert cache_key.startswith('chat:')

    assert cached_value == result.model_dump_json()

    assert (
        call.kwargs['ex']
        == settings.response_cache_ttl_seconds
    )
