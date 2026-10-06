import pytest

from decimal import Decimal
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.dependencies.auth import get_api_key_context
from app.dependencies.quota import enforce_quota
from app.main import app
from app.schemas.auth import ApiKeyContext
from app.schemas.provider import ProviderResult
from app.services.providers.router import ProviderCallResult
from app.schemas.quota import QuotaStatus
from app.services.exceptions import (
    ProviderUnavailableError,
)


@pytest.fixture
def auth_context():
    return ApiKeyContext(
        user_id=42,
        api_key_hash='a' * 64,
        plan='Pro',
        requests_limit_per_month=1000,
        requests_used_this_month=217,
        subscription_status='active',
    )


@pytest.fixture
def quota_status():
    return QuotaStatus(
        limit=1000,
        used=217,
        remaining=783,
        allowed=True,
    )


def test_chat_completion_success(
    monkeypatch,
    auth_context,
    quota_status,
):
    async def override_auth():
        return auth_context

    async def override_quota():
        return quota_status

    app.dependency_overrides[
        get_api_key_context
    ] = override_auth

    app.dependency_overrides[
        enforce_quota
    ] = override_quota


    provider_mock = AsyncMock(
        return_value=ProviderCallResult(
            result=ProviderResult(
                provider='openai',
                model='gpt-5.6-luna',
                text='Hello from OpenAI!',
                prompt_tokens=20,
                completion_tokens=10,
                stop_reason='completed',
            ),
            fallback_used=False,
        ),
    )

    usage_mock = AsyncMock()

    cache_get_mock = AsyncMock(
        return_value=None,
    )

    cache_set_mock = AsyncMock(
        return_value=None,
    )

    monkeypatch.setattr(
    'app.routers.chat.get_cached_completion',
    cache_get_mock,
    )

    monkeypatch.setattr(
    'app.routers.chat.set_cached_completion',
    cache_set_mock,
    )

    monkeypatch.setattr(
        'app.routers.chat.generate_completion',
        provider_mock,
    )

    monkeypatch.setattr(
        'app.routers.chat.create_usage_log',
        usage_mock,
    )

    client = TestClient(app)

    response = client.post(
        '/v1/chat/completions',
        headers={
            'X-API-Key': 'sk-live-test',
        },
        json={
            'model': 'gpt-5.6-luna',
            'messages': [
                {
                    'role': 'user',
                    'content': 'Hello!',
                },
            ],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data['object'] == 'chat.completion'
    assert data['model'] == 'gpt-5.6-luna'

    assert (
        data['choices'][0]['message']['content']
        == 'Hello from OpenAI!'
    )

    assert data['usage'] == {
        'prompt_tokens': 20,
        'completion_tokens': 10,
        'total_tokens': 30,
    }

    assert data['quota'] == {
        'limit': 1000,
        'used': 218,
        'remaining': 782,
    }

    usage_mock.assert_awaited_once()

    app.dependency_overrides.clear()

    call = usage_mock.await_args

    assert call.kwargs['user_id'] == 42

    assert (
        call.kwargs['api_key_hash']
        == 'a' * 64
    )

    assert call.kwargs['provider'] == 'openai'

    assert (
        call.kwargs['model']
        == 'gpt-5.6-luna'
    )

    assert call.kwargs['prompt_tokens'] == 20
    assert call.kwargs['completion_tokens'] == 10

    assert (
        call.kwargs['cost_usd']
        == Decimal('0.000016')
    )

    provider_mock.assert_awaited_once()
    cache_get_mock.assert_awaited_once()
    cache_set_mock.assert_awaited_once()

    assert call.kwargs['cache_hit'] is False
    assert call.kwargs['fallback_used'] is False


def test_chat_rejects_unsupported_model(
    auth_context,
    quota_status,
):
    async def override_auth():
        return auth_context

    async def override_quota():
        return quota_status

    app.dependency_overrides[
        get_api_key_context
    ] = override_auth

    app.dependency_overrides[
        enforce_quota
    ] = override_quota

    client = TestClient(app)

    response = client.post(
        '/v1/chat/completions',
        json={
            'model': 'expensive-unknown-model',
            'messages': [
                {
                    'role': 'user',
                    'content': 'Hello',
                },
            ],
        },
    )

    assert response.status_code == 400

    app.dependency_overrides.clear()


def test_chat_returns_503_when_provider_unavailable(
    monkeypatch,
    auth_context,
    quota_status,
):
    async def override_auth():
        return auth_context

    async def override_quota():
        return quota_status

    app.dependency_overrides[
        get_api_key_context
    ] = override_auth

    app.dependency_overrides[
        enforce_quota
    ] = override_quota

    cache_get_mock = AsyncMock(
        return_value=None,
    )

    cache_set_mock = AsyncMock(
        return_value=None,
    )

    provider_mock = AsyncMock(
        side_effect=ProviderUnavailableError(),
    )

    monkeypatch.setattr(
        'app.routers.chat.get_cached_completion',
        cache_get_mock,
    )

    monkeypatch.setattr(
        'app.routers.chat.set_cached_completion',
        cache_set_mock,
    )

    monkeypatch.setattr(
        'app.routers.chat.generate_completion',
        provider_mock,
    )

    client = TestClient(app)

    response = client.post(
        '/v1/chat/completions',
        json={
            'model': 'gpt-5.6-luna',
            'messages': [
                {
                    'role': 'user',
                    'content': 'Hello',
                },
            ],
        },
    )

    assert response.status_code == 503

    assert response.json() == {
        'detail': 'LLM provider is unavailable.',
    }

    provider_mock.assert_awaited_once()
    cache_get_mock.assert_awaited_once()
    cache_set_mock.assert_not_awaited()

    app.dependency_overrides.clear()


def test_chat_completion_cache_hit(
    monkeypatch,
    auth_context,
    quota_status,
):
    async def override_auth():
        return auth_context

    async def override_quota():
        return quota_status

    app.dependency_overrides[
        get_api_key_context
    ] = override_auth

    app.dependency_overrides[
        enforce_quota
    ] = override_quota

    cached_result = ProviderResult(
        provider='openai',
        model='gpt-5.6-luna',
        text='Cached response',
        prompt_tokens=20,
        completion_tokens=10,
        stop_reason='completed',
    )

    cache_get_mock = AsyncMock(
        return_value=cached_result,
    )

    cache_set_mock = AsyncMock()

    provider_mock = AsyncMock()

    usage_mock = AsyncMock()

    monkeypatch.setattr(
        'app.routers.chat.get_cached_completion',
        cache_get_mock,
    )

    monkeypatch.setattr(
        'app.routers.chat.set_cached_completion',
        cache_set_mock,
    )

    monkeypatch.setattr(
        'app.routers.chat.generate_completion',
        provider_mock,
    )

    monkeypatch.setattr(
        'app.routers.chat.create_usage_log',
        usage_mock,
    )

    client = TestClient(app)

    response = client.post(
        '/v1/chat/completions',
        headers={
            'X-API-Key': 'sk-live-test',
        },
        json={
            'messages': [
                {
                    'role': 'user',
                    'content': 'Hello!',
                },
            ],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data['choices'][0]['message']['content']
        == 'Cached response'
    )

    assert data['usage'] == {
        'prompt_tokens': 20,
        'completion_tokens': 10,
        'total_tokens': 30,
    }

    assert data['quota'] == {
        'limit': 1000,
        'used': 218,
        'remaining': 782,
    }

    cache_get_mock.assert_awaited_once()

    provider_mock.assert_not_awaited()

    cache_set_mock.assert_not_awaited()

    usage_mock.assert_awaited_once()

    call = usage_mock.await_args

    assert call.kwargs['provider'] == 'openai'

    assert call.kwargs['model'] == 'gpt-5.6-luna'

    assert call.kwargs['prompt_tokens'] == 0

    assert call.kwargs['completion_tokens'] == 0

    assert call.kwargs['cost_usd'] == Decimal('0')

    assert call.kwargs['cache_hit'] is True

    assert call.kwargs['fallback_used'] is False

    app.dependency_overrides.clear()
    