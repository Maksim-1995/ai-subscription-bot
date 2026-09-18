from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.openai import openai_http_client
from app.schemas.chat import (
    ChatCompletionRequest,
    ChatMessage,
)
from app.services.providers.openai import (
    create_openai_completion,
)
from app.services.exceptions import (
    ProviderRateLimitError,
    ProviderUnavailableError,
)


@pytest.mark.asyncio
async def test_openai_completion_success(
    monkeypatch,
):
    response = httpx.Response(
        status_code=200,
        json={
            'id': 'resp_test',
            'object': 'response',
            'status': 'completed',
            'model': 'gpt-5.6-luna',
            'output': [
                {
                    'type': 'message',
                    'role': 'assistant',
                    'content': [
                        {
                            'type': 'output_text',
                            'text': 'Hello!',
                        },
                    ],
                },
            ],
            'usage': {
                'input_tokens': 15,
                'output_tokens': 4,
                'total_tokens': 19,
            },
        },
    )

    post_mock = AsyncMock(
        return_value=response,
    )

    monkeypatch.setattr(
        openai_http_client,
        'post',
        post_mock,
    )

    request = ChatCompletionRequest(
        model='gpt-5.6-luna',
        messages=[
            ChatMessage(
                role='user',
                content='Hello!',
            ),
        ],
    )

    result = await create_openai_completion(
        request,
    )

    assert result.provider == 'openai'
    assert result.model == 'gpt-5.6-luna'
    assert result.text == 'Hello!'

    assert result.prompt_tokens == 15
    assert result.completion_tokens == 4
    assert result.stop_reason == 'completed'


@pytest.mark.asyncio
async def test_openai_system_message_becomes_instructions(
    monkeypatch,
):
    post_mock = AsyncMock(
        return_value=httpx.Response(
            status_code=200,
            json={
                'status': 'completed',
                'model': 'gpt-5.6-luna',
                'output': [],
                'usage': {
                    'input_tokens': 10,
                    'output_tokens': 5,
                },
            },
        ),
    )

    monkeypatch.setattr(
        openai_http_client,
        'post',
        post_mock,
    )

    request = ChatCompletionRequest(
        messages=[
            ChatMessage(
                role='system',
                content='You are a Python expert.',
            ),
            ChatMessage(
                role='user',
                content='Explain asyncio.',
            ),
        ],
    )

    await create_openai_completion(request)

    call = post_mock.await_args

    payload = call.kwargs['json']

    assert (
        payload['instructions']
        == 'You are a Python expert.'
    )

    assert payload['input'] == [
        {
            'role': 'user',
            'content': 'Explain asyncio.',
        },
    ]


@pytest.mark.asyncio
async def test_openai_rate_limit(
    monkeypatch,
):
    monkeypatch.setattr(
        openai_http_client,
        'post',
        AsyncMock(
            return_value=httpx.Response(
                status_code=429,
            ),
        ),
    )

    request = ChatCompletionRequest(
        messages=[
            ChatMessage(
                role='user',
                content='Hello!',
            ),
        ],
    )

    with pytest.raises(
        ProviderRateLimitError,
    ):
        await create_openai_completion(
            request,
        )


@pytest.mark.asyncio
async def test_openai_unavailable(
    monkeypatch,
):
    monkeypatch.setattr(
        openai_http_client,
        'post',
        AsyncMock(
            side_effect=httpx.ConnectError(
                'Connection failed.',
            ),
        ),
    )

    request = ChatCompletionRequest(
        messages=[
            ChatMessage(
                role='user',
                content='Hello!',
            ),
        ],
    )

    with pytest.raises(
        ProviderUnavailableError,
    ):
        await create_openai_completion(
            request,
        )
