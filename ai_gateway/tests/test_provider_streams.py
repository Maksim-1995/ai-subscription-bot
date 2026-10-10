import httpx
import pytest


from app.schemas.chat import (
    ChatCompletionRequest,
    ChatMessage,
)
from app.services.providers.openai import (
    create_openai_stream,
)

from app.services.providers.deepseek import (
    create_deepseek_stream,
)

from app.services.exceptions import (
    ProviderUnavailableError,
)


@pytest.mark.asyncio
async def test_openai_stream(
    monkeypatch,
):
    stream_body = (
        'data: '
        '{"type":"response.output_text.delta",'
        '"delta":"Fast"}\n\n'
        'data: '
        '{"type":"response.output_text.delta",'
        '"delta":"API"}\n\n'
        'data: '
        '{"type":"response.completed",'
        '"response":{'
        '"model":"gpt-5.6-luna",'
        '"status":"completed",'
        '"usage":{'
        '"input_tokens":10,'
        '"output_tokens":2'
        '}}}\n\n'
    )

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            content=stream_body,
            headers={
                'Content-Type': (
                    'text/event-stream'
                ),
            },
        )

    transport = httpx.MockTransport(
        handler,
    )

    async with httpx.AsyncClient(
        base_url='https://api.openai.com',
        transport=transport,
    ) as client:
        monkeypatch.setattr(
            'app.services.providers.openai.'
            'openai_http_client',
            client,
        )

        request = ChatCompletionRequest(
            model='gpt-5.6-luna',
            messages=[
                ChatMessage(
                    role='user',
                    content='Hello',
                ),
            ],
        )

        chunks = [
            chunk
            async for chunk
            in create_openai_stream(request)
        ]

    assert len(chunks) == 3

    assert chunks[0].text == 'Fast'
    assert chunks[0].done is False

    assert chunks[1].text == 'API'
    assert chunks[1].done is False

    final_chunk = chunks[2]

    assert final_chunk.done is True

    assert final_chunk.provider == 'openai'
    assert final_chunk.model == 'gpt-5.6-luna'

    assert final_chunk.prompt_tokens == 10
    assert final_chunk.completion_tokens == 2

    assert (
        final_chunk.stop_reason
        == 'completed'
    )


@pytest.mark.asyncio
async def test_deepseek_stream(
    monkeypatch,
):
    stream_body = (
        'data: '
        '{"model":"deepseek-flash",'
        '"choices":[{'
        '"delta":{"content":"Fast"},'
        '"finish_reason":null'
        '}]}\n\n'

        'data: '
        '{"model":"deepseek-flash",'
        '"choices":[{'
        '"delta":{"content":"API"},'
        '"finish_reason":"stop"'
        '}]}\n\n'

        'data: '
        '{"model":"deepseek-flash",'
        '"choices":[],'
        '"usage":{'
        '"prompt_tokens":12,'
        '"completion_tokens":2,'
        '"prompt_cache_hit_tokens":3,'
        '"prompt_cache_miss_tokens":9'
        '}}\n\n'

        'data: [DONE]\n\n'
    )

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            content=stream_body,
            headers={
                'Content-Type': (
                    'text/event-stream'
                ),
            },
        )

    transport = httpx.MockTransport(
        handler,
    )

    async with httpx.AsyncClient(
        base_url='https://api.deepseek.com',
        transport=transport,
    ) as client:
        monkeypatch.setattr(
            'app.services.providers.deepseek.'
            'deepseek_http_client',
            client,
        )

        request = ChatCompletionRequest(
            messages=[
                ChatMessage(
                    role='user',
                    content='Hello',
                ),
            ],
        )

        chunks = [
            chunk
            async for chunk
            in create_deepseek_stream(request)
        ]

    assert len(chunks) == 3

    assert chunks[0].text == 'Fast'
    assert chunks[0].done is False

    assert chunks[1].text == 'API'
    assert chunks[1].done is False

    final_chunk = chunks[2]

    assert final_chunk.done is True

    assert final_chunk.provider == 'deepseek'

    assert (
        final_chunk.model
        == 'deepseek-flash'
    )

    assert final_chunk.prompt_tokens == 12
    assert final_chunk.completion_tokens == 2

    assert (
        final_chunk.prompt_cache_hit_tokens
        == 3
    )

    assert (
        final_chunk.prompt_cache_miss_tokens
        == 9
    )

    assert final_chunk.stop_reason == 'stop'


@pytest.mark.asyncio
async def test_openai_stream_unavailable(
    monkeypatch,
):
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=503,
        )

    transport = httpx.MockTransport(
        handler,
    )

    async with httpx.AsyncClient(
        base_url='https://api.openai.com',
        transport=transport,
    ) as client:
        monkeypatch.setattr(
            'app.services.providers.openai.'
            'openai_http_client',
            client,
        )

        request = ChatCompletionRequest(
            messages=[
                ChatMessage(
                    role='user',
                    content='Hello',
                ),
            ],
        )

        with pytest.raises(
            ProviderUnavailableError,
        ):
            async for _ in create_openai_stream(
                request,
            ):
                pass
