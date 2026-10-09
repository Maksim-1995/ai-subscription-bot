"""Вызов DeepSeek и преобразование его ответа в общий формат провайдера."""

import httpx

from app.core.config import settings
from app.core.deepseek import deepseek_http_client
from app.schemas.chat import ChatCompletionRequest
from app.schemas.provider import ProviderResult
from app.services.exceptions import (
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderUnavailableError,
)


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
    payload = {
        'model': settings.deepseek_model,
        'temperature': request.temperature,
        'messages': [
            {
                'role': message.role,
                'content': message.content,
            }
            for message in request.messages
        ],
        'max_tokens': request.max_tokens,
        'thinking': {
            'type': 'disabled',
        },
    }

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
