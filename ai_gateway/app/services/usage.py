"""Сохранение статистики запросов и их стоимости в базе данных."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_log import UsageLog


async def create_usage_log(
    session: AsyncSession,
    *,
    api_key_hash: str,
    user_id: int,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: Decimal,
    cache_hit: bool = False,
    fallback_used: bool = False,
) -> UsageLog:
    """Создать запись статистики, зафиксировать сессию и обновить объект.

    Сохранить переданные счётчики, стоимость и признаки кеша/fallback
    без дополнительного расчёта. Вернуть запись с данными из БД.
    Ошибки фиксации и обновления передаются вызывающему коду.
    """

    usage_log = UsageLog(
        api_key_hash=api_key_hash,
        user_id=user_id,
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        cache_hit=cache_hit,
        fallback_used=fallback_used,
    )

    session.add(usage_log)

    # commit фиксирует все накопленные изменения этой сессии, не только лог.
    await session.commit()
    await session.refresh(usage_log)

    return usage_log
