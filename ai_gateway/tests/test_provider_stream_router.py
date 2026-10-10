import pytest

from app.schemas.chat import (
    ChatCompletionRequest,
    ChatMessage,
)
from app.schemas.provider import (
    ProviderStreamChunk,
)
from app.services.exceptions import (
    ProviderUnavailableError,
)
from app.services.providers.router import (
    stream_completion,
)


def make_request() -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model='gpt-5.6-luna',
        messages=[
            ChatMessage(
                role='user',
                content='Hello',
            ),
        ],
    )


@pytest.mark.asyncio
async def test_primary_stream_success(
    monkeypatch,
):
    async def fake_openai_stream(
        request,
    ):
        yield ProviderStreamChunk(
            provider='openai',
            model='gpt-5.6-luna',
            text='Fast',
        )

        yield ProviderStreamChunk(
            provider='openai',
            model='gpt-5.6-luna',
            text='API',
        )

        yield ProviderStreamChunk(
            provider='openai',
            model='gpt-5.6-luna',
            done=True,
            prompt_tokens=10,
            completion_tokens=2,
            stop_reason='completed',
        )

    async def fake_deepseek_stream(
        request,
    ):
        raise AssertionError(
            'DeepSeek must not be called',
        )

        yield

    monkeypatch.setattr(
        'app.services.providers.router.'
        'create_openai_stream',
        fake_openai_stream,
    )

    monkeypatch.setattr(
        'app.services.providers.router.'
        'create_deepseek_stream',
        fake_deepseek_stream,
    )

    chunks = [
        chunk
        async for chunk
        in stream_completion(
            make_request(),
        )
    ]

    assert len(chunks) == 3

    assert chunks[0].text == 'Fast'
    assert chunks[1].text == 'API'

    assert chunks[2].done is True

    assert all(
        chunk.provider == 'openai'
        for chunk in chunks
    )

    assert all(
        chunk.fallback_used is False
        for chunk in chunks
    )


@pytest.mark.asyncio
async def test_stream_fallback_before_first_chunk(
    monkeypatch,
):
    async def fake_openai_stream(
        request,
    ):
        if False:
            yield

        raise ProviderUnavailableError

    async def fake_deepseek_stream(
        request,
    ):
        yield ProviderStreamChunk(
            provider='deepseek',
            model='deepseek-flash',
            text='Hello',
        )

        yield ProviderStreamChunk(
            provider='deepseek',
            model='deepseek-flash',
            done=True,
            prompt_tokens=10,
            completion_tokens=1,
            stop_reason='stop',
        )

    monkeypatch.setattr(
        'app.services.providers.router.'
        'create_openai_stream',
        fake_openai_stream,
    )

    monkeypatch.setattr(
        'app.services.providers.router.'
        'create_deepseek_stream',
        fake_deepseek_stream,
    )

    chunks = [
        chunk
        async for chunk
        in stream_completion(
            make_request(),
        )
    ]

    assert len(chunks) == 2

    assert chunks[0].provider == 'deepseek'
    assert chunks[0].text == 'Hello'

    assert chunks[1].provider == 'deepseek'
    assert chunks[1].done is True

    assert all(
        chunk.fallback_used is True
        for chunk in chunks
    )


@pytest.mark.asyncio
async def test_no_fallback_after_stream_started(
    monkeypatch,
):
    async def fake_openai_stream(
        request,
    ):
        yield ProviderStreamChunk(
            provider='openai',
            model='gpt-5.6-luna',
            text='Fast',
        )

        raise ProviderUnavailableError

    async def fake_deepseek_stream(
        request,
    ):
        raise AssertionError(
            'DeepSeek must not be called '
            'after stream started',
        )

        yield

    monkeypatch.setattr(
        'app.services.providers.router.'
        'create_openai_stream',
        fake_openai_stream,
    )

    monkeypatch.setattr(
        'app.services.providers.router.'
        'create_deepseek_stream',
        fake_deepseek_stream,
    )

    received_chunks = []

    with pytest.raises(
        ProviderUnavailableError,
    ):
        async for chunk in stream_completion(
            make_request(),
        ):
            received_chunks.append(
                chunk,
            )

    assert len(received_chunks) == 1

    assert (
        received_chunks[0].text
        == 'Fast'
    )

    assert (
        received_chunks[0].provider
        == 'openai'
    )
