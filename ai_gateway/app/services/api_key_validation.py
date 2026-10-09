"""Проверка API-ключей через Core API с краткосрочным кешированием в Redis."""

import hashlib
import json
import logging

from redis.exceptions import RedisError

from app.core.redis import redis_client
from app.schemas.auth import ApiKeyValidationResult
from app.services.core_api import validate_api_key_with_core


logger = logging.getLogger(__name__)


# Отрицательный результат хранится меньше, чтобы быстрее увидеть изменение
# ключа или подписки после повторной проверки через Core API.
VALID_TTL_SECONDS = 60
INVALID_TTL_SECONDS = 10


def hash_api_key(raw_api_key: str) -> str:
    """Вернуть SHA-256 ключа для кеша и учета без хранения исходного секрета."""
    return hashlib.sha256(
        raw_api_key.encode('utf-8'),
    ).hexdigest()


def build_cache_key(raw_api_key: str) -> str:
    """Сформировать ключ Redis с префиксом apikey и хешем API-ключа."""
    api_key_hash = hash_api_key(raw_api_key)

    return f'apikey:{api_key_hash}'


async def validate_api_key(
    raw_api_key: str,
) -> ApiKeyValidationResult:
    """Получить результат из кеша или запросить проверку в Core API.

    Успешная проверка кешируется на 60 секунд, отрицательная — на 10 секунд.
    Ошибки Redis не блокируют проверку; ошибки Core API передаются вызывающему
    коду и не кешируются.
    """
    cache_key = build_cache_key(
        raw_api_key,
    )

    try:
        cached = await redis_client.get(
            cache_key,
        )
    except RedisError:
        logger.warning(
            'Redis unavailable during API key cache read.',
        )
        cached = None

    if cached is not None:
        return ApiKeyValidationResult(
            **json.loads(cached),
        )

    result = await validate_api_key_with_core(
        raw_api_key,
    )

    ttl = (
        VALID_TTL_SECONDS
        if result.valid
        else INVALID_TTL_SECONDS
    )

    try:
        await redis_client.set(
            cache_key,
            result.model_dump_json(),
            ex=ttl,
        )
    except RedisError:
        logger.warning(
            'Redis unavailable during API key cache write.',
        )

    return result
