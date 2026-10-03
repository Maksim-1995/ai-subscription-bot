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
    key = build_response_cache_key(request)

    try:
        cached = await redis_client.get(key)

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
    key = build_response_cache_key(request)

    try:
        await redis_client.set(
            key,
            result.model_dump_json(),
            ex=settings.response_cache_ttl_seconds,
        )

    except RedisError:
        logger.warning(
            'Redis response cache write failed',
            exc_info=True,
        )
