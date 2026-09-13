import httpx

from app.core.config import settings
from app.core.http import http_client
from app.schemas.auth import ApiKeyValidationResult
from app.services.exceptions import CoreApiUnavailableError


async def validate_api_key_with_core(
    raw_api_key: str,
) -> ApiKeyValidationResult:
    url = (
        f'{settings.core_api_url}'
        '/internal/api-keys/validate/'
    )

    try:
        response = await http_client.post(
            url,
            headers={
                'X-Internal-Token': (
                    settings.internal_api_token
                ),
            },
            json={
                'api_key': raw_api_key,
            },
        )
    except httpx.RequestError as exc:
        raise CoreApiUnavailableError from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise CoreApiUnavailableError from exc

    if response.status_code == 200:
        return ApiKeyValidationResult(
            **data,
        )

    reason = data.get('reason')

    if (
        response.status_code == 404
        and reason == 'not_found'
    ):
        return ApiKeyValidationResult(
            valid=False,
            reason='not_found',
        )

    if (
        response.status_code == 401
        and reason == 'expired'
    ):
        return ApiKeyValidationResult(
            valid=False,
            reason='expired',
        )

    if (
        response.status_code == 401
        and reason == 'invalid_token'
    ):
        raise CoreApiUnavailableError

    if response.status_code >= 500:
        raise CoreApiUnavailableError

    raise CoreApiUnavailableError