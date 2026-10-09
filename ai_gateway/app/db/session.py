"""Асинхронный движок PostgreSQL и фабрика сессий SQLAlchemy."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


# Проверка соединения перед выдачей из пула позволяет заменить устаревшее.
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)

# После commit загруженные атрибуты остаются доступны без нового SQL-запроса.
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Выдать сессию FastAPI-зависимости и закрыть её после обработки запроса.

    Commit выполняет вызывающий сервис. При выходе незавершённая транзакция
    откатывается, а соединение возвращается в пул.
    """

    async with async_session_factory() as session:
        yield session
