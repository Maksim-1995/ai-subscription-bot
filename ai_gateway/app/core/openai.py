import httpx

from app.core.config import settings


openai_http_client = httpx.AsyncClient(
    base_url=settings.openai_base_url,
    timeout=httpx.Timeout(
        settings.openai_request_timeout,
    ),
)
