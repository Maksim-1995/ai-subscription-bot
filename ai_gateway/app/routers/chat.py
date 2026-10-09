"""HTTP-маршрут генерации ответа с кешем, учетом расхода и месячной квотой."""

import time
import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.dependencies.auth import get_api_key_context
from app.dependencies.quota import enforce_quota
from app.schemas.auth import ApiKeyContext
from app.schemas.chat import (
    AssistantMessage,
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatUsage,
    QuotaInfo,
)
from app.schemas.provider import ProviderResult
from app.schemas.quota import QuotaStatus
from app.services.exceptions import (
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderUnavailableError,
)
from app.services.pricing import (
    calculate_cost_usd,
    is_supported_model,
)
from app.services.providers.router import (
    generate_completion,
)
from app.services.response_cache import (
    get_cached_completion,
    set_cached_completion,
)
from app.services.usage import create_usage_log


router = APIRouter(
    prefix='/v1',
    tags=['chat'],
)


def build_chat_response(
    provider_result: ProviderResult,
    quota: QuotaStatus,
) -> ChatCompletionResponse:
    """Собрать ответ клиенту и учесть текущий запрос в переданном снимке квоты.

    ``quota`` содержит счетчики до обработки запроса. Данные о токенах
    берутся из результата провайдера, в том числе при чтении из кеша.
    """
    used_after_request = quota.used + 1

    remaining_after_request = max(
        quota.limit - used_after_request,
        0,
    )

    return ChatCompletionResponse(
        id=f'chatcmpl-{uuid.uuid4().hex}',
        created=int(time.time()),
        model=provider_result.model,
        choices=[
            ChatChoice(
                index=0,
                message=AssistantMessage(
                    content=provider_result.text,
                ),
                finish_reason=(
                    provider_result.stop_reason
                ),
            ),
        ],
        usage=ChatUsage(
            prompt_tokens=(
                provider_result.prompt_tokens
            ),
            completion_tokens=(
                provider_result.completion_tokens
            ),
            total_tokens=(
                provider_result.prompt_tokens
                + provider_result.completion_tokens
            ),
        ),
        quota=QuotaInfo(
            limit=quota.limit,
            used=used_after_request,
            remaining=remaining_after_request,
        ),
    )


@router.post(
    '/chat/completions',
    response_model=ChatCompletionResponse,
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    auth_context: Annotated[
        ApiKeyContext,
        Depends(get_api_key_context),
    ],
    quota: Annotated[
        QuotaStatus,
        Depends(enforce_quota),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_session),
    ],
) -> ChatCompletionResponse:
    """Получить ответ из кеша или от провайдера и сохранить запись расхода.

    FastAPI проверяет API-ключ и квоту через зависимости до вызова обработчика.
    Каждый успешный запрос расходует квоту, включая попадание в кеш.
    Неизвестная модель приводит к HTTP 400, недоступность провайдера — к 503,
    отклоненный провайдером запрос — к 502.
    """
    model = (
        request.model
        or settings.openai_model
    )

    if not is_supported_model(model):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                'error': 'unsupported_model',
                'model': model,
            },
        )

    cached_result = await get_cached_completion(
        request,
    )

    if cached_result is not None:
        # Кешированный ответ расходует квоту, но не создает затрат у провайдера.
        # В журнале токены равны нулю; в ответе сохраняется usage из кеша.
        await create_usage_log(
            session=session,
            api_key_hash=auth_context.api_key_hash,
            user_id=auth_context.user_id,
            provider=cached_result.provider,
            model=cached_result.model,
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=Decimal('0'),
            cache_hit=True,
            fallback_used=False,
        )

        return build_chat_response(
            provider_result=cached_result,
            quota=quota,
        )

    try:
        provider_call = await generate_completion(
            request,
        )

    except ProviderRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='LLM provider rate limit exceeded.',
        ) from exc

    except ProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='LLM provider is unavailable.',
        ) from exc

    except ProviderRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='LLM provider rejected the request.',
        ) from exc

    provider_result = provider_call.result
    fallback_used = provider_call.fallback_used

    cost_usd = calculate_cost_usd(
        provider_result.model,
        provider_result.prompt_tokens,
        provider_result.completion_tokens,
        provider=provider_result.provider,
        prompt_cache_hit_tokens=(
            provider_result.prompt_cache_hit_tokens
        ),
        prompt_cache_miss_tokens=(
            provider_result.prompt_cache_miss_tokens
        ),
    )

    # Запись расхода фиксируется в БД до сохранения ответа в Redis.
    await create_usage_log(
        session=session,
        api_key_hash=auth_context.api_key_hash,
        user_id=auth_context.user_id,
        provider=provider_result.provider,
        model=provider_result.model,
        prompt_tokens=(
            provider_result.prompt_tokens
        ),
        completion_tokens=(
            provider_result.completion_tokens
        ),
        cost_usd=cost_usd,
        cache_hit=False,
        fallback_used=fallback_used,
    )

    await set_cached_completion(
        request,
        provider_result,
    )

    return build_chat_response(
        provider_result=provider_result,
        quota=quota,
    )
