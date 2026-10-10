"""Выбор провайдера: OpenAI с резервным вызовом DeepSeek."""

import logging
from dataclasses import dataclass

from app.schemas.chat import ChatCompletionRequest
from app.schemas.provider import ProviderResult, ProviderStreamChunk
from app.services.exceptions import (
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.services.providers.deepseek import (
    create_deepseek_completion,
    create_deepseek_stream,
)
from app.services.providers.openai import (
    create_openai_completion,
    create_openai_stream,
)

from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProviderCallResult:
    """Ответ провайдера и признак использования резервного вызова."""

    result: ProviderResult
    fallback_used: bool


async def generate_completion(
    request: ChatCompletionRequest,
) -> ProviderCallResult:
    """Вызвать OpenAI, переключившись на DeepSeek при временном сбое.

    Ошибки запроса к OpenAI и ошибки резервного провайдера передаются
    вызывающему коду. Успешный ответ содержит признак fallback_used.
    """
    try:
        result = await create_openai_completion(
            request,
        )

        return ProviderCallResult(
            result=result,
            fallback_used=False,
        )

    # Резервный вызов выполняется только при rate limit или недоступности;
    # другие ошибки не становятся поводом повторять запрос у DeepSeek.
    except (
        ProviderRateLimitError,
        ProviderUnavailableError,
    ) as exc:
        logger.warning(
            'OpenAI unavailable (%s), switching to DeepSeek',
            type(exc).__name__,
        )

        result = await create_deepseek_completion(
            request,
        )

        return ProviderCallResult(
            result=result,
            fallback_used=True,
        )


async def stream_completion(
    request: ChatCompletionRequest,
) -> AsyncIterator[ProviderStreamChunk]:
    stream_started = False

    try:
        async for chunk in create_openai_stream(
            request,
        ):
            stream_started = True

            yield chunk

        return

    except (
        ProviderRateLimitError,
        ProviderUnavailableError,
    ) as exc:
        if stream_started:
            logger.error(
                'OpenAI stream failed after '
                'response started: %s',
                type(exc).__name__,
            )

            raise

        logger.warning(
            'OpenAI stream unavailable (%s), '
            'switching to DeepSeek',
            type(exc).__name__,
        )

    async for chunk in create_deepseek_stream(
        request,
    ):
        yield chunk.model_copy(
            update={
                'fallback_used': True,
            },
        )
