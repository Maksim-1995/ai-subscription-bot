"""Общий асинхронный HTTP-клиент для API DeepSeek."""

import httpx

from app.core.config import settings


# Пул соединений и таймаут общие для всех обращений к провайдеру.
deepseek_http_client = httpx.AsyncClient(
    base_url=settings.deepseek_base_url,
    timeout=settings.deepseek_request_timeout,
)
