import logging
from dataclasses import dataclass

from app.schemas.chat import ChatCompletionRequest
from app.schemas.provider import ProviderResult
from app.services.exceptions import (
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.services.providers.deepseek import (
    create_deepseek_completion,
)
from app.services.providers.openai import (
    create_openai_completion,
)


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProviderCallResult:
    result: ProviderResult
    fallback_used: bool


async def generate_completion(
    request: ChatCompletionRequest,
) -> ProviderCallResult:
    try:
        result = await create_openai_completion(
            request,
        )

        return ProviderCallResult(
            result=result,
            fallback_used=False,
        )

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
