"""Общий HTTP-клиент для обращений к OpenAI-совместимому API."""

import httpx

from app.core.config import settings


# Клиент сохраняет пул соединений между запросами и закрывается в lifespan.
openai_http_client = httpx.AsyncClient(
    base_url=settings.openai_base_url,
    timeout=httpx.Timeout(
        settings.openai_request_timeout,
    ),
)
