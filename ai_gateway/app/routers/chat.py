import time
import uuid
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
from app.services.providers.openai import (
    create_openai_completion,
)
from app.services.usage import create_usage_log


router = APIRouter(
    prefix='/v1',
    tags=['chat'],
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

    try:
        provider_result = (
            await create_openai_completion(
                request,
            )
        )

    except ProviderRateLimitError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail='LLM provider temporarily unavailable.',
        ) from exc

    except ProviderUnavailableError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail='LLM provider temporarily unavailable.',
        ) from exc

    except ProviderRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='LLM provider rejected the request.',
        ) from exc

    cost_usd = calculate_cost_usd(
        model=provider_result.model,
        prompt_tokens=(
            provider_result.prompt_tokens
        ),
        completion_tokens=(
            provider_result.completion_tokens
        ),
    )

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
        fallback_used=False,
    )

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
