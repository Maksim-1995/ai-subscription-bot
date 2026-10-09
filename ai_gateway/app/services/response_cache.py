"""Кеширование готовых ответов провайдеров в Redis с ограниченным TTL."""

import hashlib
import json
import logging

from redis.exceptions import RedisError

from app.core.config import settings
from app.core.redis import redis_client
from app.schemas.chat import ChatCompletionRequest
from app.schemas.provider import ProviderResult


logger = logging.getLogger(__name__)

CACHE_PREFIX = 'chat:'


def build_response_cache_key(
    request: ChatCompletionRequest,
) -> str:
    """Построить ключ chat:<SHA-256> из модели, сообщений и температуры.

    При отсутствии модели использовать модель OpenAI из настроек.
    Стабильная JSON-сериализация даёт одинаковый ключ для одинаковых
    значений этих полей.
    """
    # Текущий ключ не включает max_tokens, stream, пользователя или API-ключ:
    # запросы с одинаковыми полями ниже обращаются к общей записи кеша.
    payload = {
        'model': (
            request.model
            or settings.openai_model
        ),
        'messages': [
            message.model_dump()
            for message in request.messages
        ],
        'temperature': request.temperature,
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
    )

    digest = hashlib.sha256(
        serialized.encode('utf-8'),
    ).hexdigest()

    return f'{CACHE_PREFIX}{digest}'


async def get_cached_completion(
    request: ChatCompletionRequest,
) -> ProviderResult | None:
    """Прочитать ответ из кеша или вернуть None при промахе/ошибке Redis.

    Если JSON не проходит проверку ProviderResult, попытаться удалить
    повреждённую запись и считать обращение промахом кеша.
    """
    key = build_response_cache_key(request)

    try:
        cached = await redis_client.get(key)

    # Сбой Redis трактуется как промах, позволяя продолжить вызов провайдера.
    except RedisError:
        logger.warning(
            'Redis response cache read failed',
            exc_info=True,
        )
        return None

    if cached is None:
        return None

    if isinstance(cached, bytes):
        cached = cached.decode('utf-8')

    try:
        return ProviderResult.model_validate_json(
            cached,
        )

    except ValueError:
        logger.warning(
            'Invalid response cache value: %s',
            key,
        )

        try:
            await redis_client.delete(key)
        except RedisError:
            pass

        return None


async def set_cached_completion(
    request: ChatCompletionRequest,
    result: ProviderResult,
) -> None:
    """Сохранить ответ на настроенный TTL, подавив ошибки записи в Redis."""
    key = build_response_cache_key(request)

    try:
        await redis_client.set(
            key,
            result.model_dump_json(),
            ex=settings.response_cache_ttl_seconds,
        )

    # Кеш необязателен: ошибка записи не должна отменять готовый ответ.
    except RedisError:
        logger.warning(
            'Redis response cache write failed',
            exc_info=True,
        )
