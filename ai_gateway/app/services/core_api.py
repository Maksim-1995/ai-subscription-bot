"""Клиент внутреннего эндпоинта Core API для проверки ключа и подписки."""

import httpx

from app.core.config import settings
from app.core.http import http_client
from app.schemas.auth import ApiKeyValidationResult
from app.services.exceptions import CoreApiUnavailableError


async def validate_api_key_with_core(
    raw_api_key: str,
) -> ApiKeyValidationResult:
    """Отправить ключ в Core API, используя внутренний токен сервиса.

    HTTP 200 преобразуется в результат проверки, а известные причины not_found
    и expired — в отрицательный результат. Ошибки транспорта, невалидный JSON
    и остальные HTTP-ответы приводят к CoreApiUnavailableError.
    """
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
        # Ошибка внутреннего токена относится к связи сервисов, а не к ключу
        # пользователя: ее нельзя кешировать как отрицательную проверку ключа.
        raise CoreApiUnavailableError

    if response.status_code >= 500:
        raise CoreApiUnavailableError

    raise CoreApiUnavailableError