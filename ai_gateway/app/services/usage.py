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
    """Create a new usage log entry in the database."""

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

    await session.commit()
    await session.refresh(usage_log)

    return usage_log
