import hashlib
import json

from app.core.redis import redis_client
from app.schemas.auth import ApiKeyValidationResult
from app.services.core_api import validate_api_key_with_core


VALID_TTL_SECONDS = 60
INVALID_TTL_SECONDS = 10


def hash_api_key(raw_api_key: str) -> str:
    return hashlib.sha256(
        raw_api_key.encode('utf-8'),
    ).hexdigest()


def build_cache_key(raw_api_key: str) -> str:
    api_key_hash = hash_api_key(raw_api_key)

    return f'apikey:{api_key_hash}'


async def validate_api_key(
    raw_api_key: str,
) -> ApiKeyValidationResult:
    cache_key = build_cache_key(
        raw_api_key,
    )

    cached = await redis_client.get(
        cache_key,
    )

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

    await redis_client.set(
        cache_key,
        result.model_dump_json(),
        ex=ttl,
    )

    return result
