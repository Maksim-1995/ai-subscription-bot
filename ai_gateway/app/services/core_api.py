import httpx

from app.core.config import settings
from app.schemas.auth import ApiKeyValidationResult
from app.services.exceptions import CoreApiUnavailableError


async def validate_api_key_with_core(
    raw_api_key: str,
) -> ApiKeyValidationResult:
    url = (
        f'{settings.core_api_url}'
        '/internal/api-keys/validate/'
    )

    headers = {
        'X-Internal-Token': settings.internal_api_token,
    }

    try:
        async with httpx.AsyncClient(
            timeout=5.0,
        ) as client:
            response = await client.post(
                url,
                headers=headers,
                json={
                    'api_key': raw_api_key,
                },
            )
    except httpx.RequestError as exc:
        raise CoreApiUnavailableError from exc

    if response.status_code == 200:
        return ApiKeyValidationResult(
            **response.json(),
        )

    if response.status_code in (401, 404):
        data = response.json()

        return ApiKeyValidationResult(
            valid=False,
            reason=data.get('reason'),
        )

    if response.status_code >= 500:
        raise CoreApiUnavailableError

    response.raise_for_status()

    return ApiKeyValidationResult(
        **response.json(),
    )
