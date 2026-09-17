from unittest.mock import AsyncMock

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.dependencies.auth import get_api_key_context
from app.schemas.auth import (
    ApiKeyContext,
    ApiKeyValidationResult,
)

from app.services.exceptions import CoreApiUnavailableError


test_app = FastAPI()


@test_app.get('/protected')
async def protected(
    context: ApiKeyContext = Depends(
        get_api_key_context,
    ),
):
    return {
        'user_id': context.user_id,
        'plan': context.plan,
    }


client = TestClient(test_app)


def test_missing_api_key_returns_401():
    response = client.get(
        '/protected',
    )

    assert response.status_code == 401


def test_valid_api_key_allows_request(
    monkeypatch,
):
    validation_mock = AsyncMock(
        return_value=ApiKeyValidationResult(
            valid=True,
            user_id=10,
            plan='Pro',
            requests_limit_per_month=1000,
            requests_used_this_month=100,
            subscription_status='active',
        )
    )

    monkeypatch.setattr(
        'app.dependencies.auth.validate_api_key',
        validation_mock,
    )

    response = client.get(
        '/protected',
        headers={
            'X-API-Key': 'sk-live-test',
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        'user_id': 10,
        'plan': 'Pro',
    }


def test_invalid_api_key_returns_401(
    monkeypatch,
):
    monkeypatch.setattr(
        'app.dependencies.auth.validate_api_key',
        AsyncMock(
            return_value=ApiKeyValidationResult(
                valid=False,
                reason='not_found',
            )
        ),
    )

    response = client.get(
        '/protected',
        headers={
            'X-API-Key': 'sk-live-invalid',
        },
    )

    assert response.status_code == 401


def test_expired_subscription_returns_403(
    monkeypatch,
):
    monkeypatch.setattr(
        'app.dependencies.auth.validate_api_key',
        AsyncMock(
            return_value=ApiKeyValidationResult(
                valid=False,
                reason='expired',
            )
        ),
    )

    response = client.get(
        '/protected',
        headers={
            'X-API-Key': 'sk-live-test',
        },
    )

    assert response.status_code == 403


def test_core_api_unavailable_returns_503(
    monkeypatch,
):
    monkeypatch.setattr(
        'app.dependencies.auth.validate_api_key',
        AsyncMock(
            side_effect=CoreApiUnavailableError,
        ),
    )

    response = client.get(
        '/protected',
        headers={
            'X-API-Key': 'sk-live-test',
        },
    )

    assert response.status_code == 503