"""Вызов DeepSeek и преобразование его ответа в общий формат провайдера."""

import json
import httpx

from collections.abc import AsyncIterator
from app.core.config import settings
from app.core.deepseek import deepseek_http_client
from app.schemas.chat import ChatCompletionRequest
from app.schemas.provider import (
    ProviderResult,
    ProviderStreamChunk,
)
from app.services.exceptions import (
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderUnavailableError,
)


def build_deepseek_payload(
    request: ChatCompletionRequest,
    *,
    stream: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        'model': settings.deepseek_model,
        'messages': [
            {
                'role': message.role,
                'content': message.content,
            }
            for message in request.messages
        ],
        'max_tokens': request.max_tokens,
        'temperature': request.temperature,
        'thinking': {
            'type': 'disabled',
        },
    }

    if stream:
        payload['stream'] = True

        payload['stream_options'] = {
            'include_usage': True,
        }

    return payload


async def create_deepseek_completion(
        request: ChatCompletionRequest,
) -> ProviderResult:
    """Получить ответ DeepSeek для модели из настроек Gateway.

    Передать сообщения, температуру и лимит выходных токенов, отключив
    режим thinking. Модель из запроса не используется.

    Raises:
        ProviderRateLimitError: DeepSeek вернул HTTP 429.
        ProviderUnavailableError: Ошибка соединения, таймаут, HTTP 5xx,
            некорректный JSON или отсутствие вариантов ответа.
        ProviderRequestError: Получен другой ответ с HTTP-статусом >= 400.
    """
    payload = build_deepseek_payload(request)

    try:
        response = await deepseek_http_client.post(
            '/chat/completions',
            headers={
                'Authorization': (
                    f'Bearer {settings.deepseek_api_key}'
                ),
                'Content-Type': 'application/json',
            },
            json=payload,
        )

    except httpx.TimeoutException as exc:
        raise ProviderUnavailableError from exc

    except httpx.RequestError as exc:
        raise ProviderUnavailableError from exc

    if response.status_code == 429:
        raise ProviderRateLimitError

    if response.status_code >= 500:
        raise ProviderUnavailableError

    if response.status_code >= 400:
        try:
            error_data = response.json()
            message = (
                error_data
                .get('error', {})
                .get('message', response.text)
            )
        except ValueError:
            message = response.text

        raise ProviderRequestError(
            status_code=response.status_code,
            message=message,
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderUnavailableError from exc

    choices = data.get('choices') or []

    if not choices:
        raise ProviderUnavailableError

    choice = choices[0]

    message = choice.get('message') or {}

    # Это кеш входного промпта у DeepSeek, отдельный от кеша ответов в Redis.
    # Отсутствующие счётчики ниже заменяются нулями без локального подсчёта.
    usage = data.get('usage') or {}

    return ProviderResult(
        provider='deepseek',
        model=data.get(
            'model',
            settings.deepseek_model,
        ),
        text=message.get('content', ''),
        prompt_tokens=usage.get(
            'prompt_tokens',
            0,
        ),
        completion_tokens=usage.get(
            'completion_tokens',
            0,
        ),
        prompt_cache_hit_tokens=usage.get(
            'prompt_cache_hit_tokens',
            0,
        ),
        prompt_cache_miss_tokens=usage.get(
            'prompt_cache_miss_tokens',
            0,
        ),
        stop_reason=choice.get(
            'finish_reason',
        ),
    )


async def create_deepseek_stream(
    request: ChatCompletionRequest,
) -> AsyncIterator[ProviderStreamChunk]:
    payload = build_deepseek_payload(
        request,
        stream=True,
    )

    model = settings.deepseek_model

    prompt_tokens = 0
    completion_tokens = 0

    prompt_cache_hit_tokens = 0
    prompt_cache_miss_tokens = 0

    stop_reason: str | None = None

    try:
        async with deepseek_http_client.stream(
            'POST',
            '/chat/completions',
            headers={
                'Authorization': (
                    f'Bearer {settings.deepseek_api_key}'
                ),
                'Content-Type': 'application/json',
            },
            json=payload,
        ) as response:

            if response.status_code == 429:
                raise ProviderRateLimitError

            if response.status_code >= 500:
                raise ProviderUnavailableError

            if response.status_code >= 400:
                await response.aread()

                try:
                    error_data = response.json()

                    message = (
                        error_data
                        .get('error', {})
                        .get(
                            'message',
                            response.text,
                        )
                    )

                except ValueError:
                    message = response.text

                raise ProviderRequestError(
                    status_code=response.status_code,
                    message=message,
                )

            async for line in response.aiter_lines():
                if not line.startswith('data:'):
                    continue

                raw_data = line[5:].strip()

                if not raw_data:
                    continue

                if raw_data == '[DONE]':
                    yield ProviderStreamChunk(
                        provider='deepseek',
                        model=model,
                        done=True,
                        prompt_tokens=(
                            prompt_tokens
                        ),
                        completion_tokens=(
                            completion_tokens
                        ),
                        prompt_cache_hit_tokens=(
                            prompt_cache_hit_tokens
                        ),
                        prompt_cache_miss_tokens=(
                            prompt_cache_miss_tokens
                        ),
                        stop_reason=stop_reason,
                    )

                    return

                try:
                    data = json.loads(
                        raw_data,
                    )

                except json.JSONDecodeError as exc:
                    raise (
                        ProviderUnavailableError
                    ) from exc

                model = data.get(
                    'model',
                    model,
                )

                usage = data.get('usage')

                if usage:
                    prompt_tokens = usage.get(
                        'prompt_tokens',
                        prompt_tokens,
                    )

                    completion_tokens = (
                        usage.get(
                            'completion_tokens',
                            completion_tokens,
                        )
                    )

                    prompt_cache_hit_tokens = (
                        usage.get(
                            'prompt_cache_hit_tokens',
                            prompt_cache_hit_tokens,
                        )
                    )

                    prompt_cache_miss_tokens = (
                        usage.get(
                            'prompt_cache_miss_tokens',
                            prompt_cache_miss_tokens,
                        )
                    )

                choices = (
                    data.get('choices')
                    or []
                )

                if not choices:
                    continue

                choice = choices[0]

                if (
                    choice.get('finish_reason')
                    is not None
                ):
                    stop_reason = choice.get(
                        'finish_reason',
                    )

                delta = (
                    choice.get('delta')
                    or {}
                )

                text = delta.get(
                    'content',
                    '',
                )

                if text:
                    yield ProviderStreamChunk(
                        provider='deepseek',
                        model=model,
                        text=text,
                    )

            raise ProviderUnavailableError

    except httpx.TimeoutException as exc:
        raise ProviderUnavailableError from exc

    except httpx.RequestError as exc:
        raise ProviderUnavailableError from exc
