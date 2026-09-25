import httpx

from app.core.config import settings


deepseek_http_client = httpx.AsyncClient(
    base_url=settings.deepseek_base_url,
    timeout=settings.deepseek_request_timeout,
)
