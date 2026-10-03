from app.schemas.chat import (
    ChatCompletionRequest,
    ChatMessage,
)
from app.services.response_cache import (
    build_response_cache_key,
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
