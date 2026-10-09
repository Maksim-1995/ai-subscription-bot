"""Общий асинхронный HTTP-клиент для внутренних запросов в Core API."""

import httpx


# Один клиент переиспользует соединения; его закрывает lifespan приложения.
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(5.0),
)
