"""Общий асинхронный Redis-клиент для кешей Gateway."""

from redis.asyncio import Redis

from app.core.config import settings


# Пул соединений используется повторно, а ответы декодируются в строки.
# Клиент закрывается в lifespan приложения.
redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
)
