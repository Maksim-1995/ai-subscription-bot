from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sqlalchemy import text

from app.db.session import async_session_factory
from app.services.exceptions import QuotaExceededError


from app.core.config import settings
from app.core.redis import redis_client
from app.core.http import http_client
from ai_gateway.app.core.openai import openai_http_client
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await http_client.aclose()
    await redis_client.aclose()
    await openai_http_client.aclose()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    lifespan=lifespan,
)


@app.get('/health')
async def health():
    async with async_session_factory() as session:
        await session.execute(
            text('SELECT 1'),
        )

    await redis_client.ping()

    return {
        'status': 'ok',
        'database': 'ok',
        'redis': 'ok',
    }


@app.exception_handler(QuotaExceededError)
async def quota_exceeded_handler(
    request: Request,
    exc: QuotaExceededError,
):
    return JSONResponse(
        status_code=429,
        content={
            'error': 'quota_exceeded',
        },
        headers={
            'X-RateLimit-Limit': str(exc.limit),
            'X-RateLimit-Remaining': '0',
        },
    )
