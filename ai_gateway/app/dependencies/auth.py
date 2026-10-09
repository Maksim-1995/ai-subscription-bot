"""Аутентификация запросов по X-API-Key и подготовка контекста подписки."""

from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.schemas.auth import ApiKeyContext
from app.services.api_key_validation import (
    hash_api_key,
    validate_api_key,
)
from app.services.exceptions import CoreApiUnavailableError


api_key_header = APIKeyHeader(
    name='X-API-Key',
    auto_error=False,
)


async def get_api_key_context(
    raw_api_key: Annotated[
        str | None,
        Security(api_key_header),
    ],
) -> ApiKeyContext:
    """Проверить ключ и вернуть данные пользователя для зависимых обработчиков.

    Отсутствующий или неверный ключ приводит к HTTP 401, истекшая подписка —
    к HTTP 403. Недоступность Core API или неполный успешный ответ дают HTTP 503.
    """
    if not raw_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='API key is required.',
        )

    try:
        result = await validate_api_key(
            raw_api_key,
        )
    except CoreApiUnavailableError as exc:
        # Без подтвержденной проверки доступ закрыт: сбой Core API не дает
        # разрешения на выполнение запроса.
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail='Authentication service unavailable.',
        ) from exc

    if not result.valid:
        if result.reason == 'expired':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Subscription is not active.',
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid API key.',
        )

    if (
        result.user_id is None
        or result.plan is None
        or result.requests_limit_per_month is None
        or result.subscription_status is None
    ):
        # Одного valid=True недостаточно: контекст требует данных подписки.
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail='Invalid authentication response.',
        )

    return ApiKeyContext(
        user_id=result.user_id,
        api_key_hash=hash_api_key(
            raw_api_key,
        ),
        plan=result.plan,
        requests_limit_per_month=(
            result.requests_limit_per_month
        ),
        requests_used_this_month=(
            result.requests_used_this_month
        ),
        subscription_status=(
            result.subscription_status
        ),
    )
