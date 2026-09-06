from contextlib import asynccontextmanager

from fastapi import FastAPI

from sqlalchemy import text

from app.db.session import async_session_factory


from app.core.config import settings
from app.core.redis import redis_client
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

    await redis_client.aclose()
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
