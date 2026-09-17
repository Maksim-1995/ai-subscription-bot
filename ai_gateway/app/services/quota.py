from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_log import UsageLog
from app.schemas.quota import QuotaStatus


def get_month_boundaries() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)

    month_start = datetime(
        year=now.year,
        month=now.month,
        day=1,
        tzinfo=timezone.utc,
    )

    if now.month == 12:
        next_month_start = datetime(
            year=now.year + 1,
            month=1,
            day=1,
            tzinfo=timezone.utc,
        )
    else:
        next_month_start = datetime(
            year=now.year,
            month=now.month + 1,
            day=1,
            tzinfo=timezone.utc,
        )

    return month_start, next_month_start


async def get_requests_used_this_month(
    session: AsyncSession,
    user_id: int,
) -> int:
    month_start, next_month_start = get_month_boundaries()

    statement = (
        select(func.count(UsageLog.id))
        .where(
            UsageLog.user_id == user_id,
            UsageLog.created_at >= month_start,
            UsageLog.created_at < next_month_start,
        )
    )

    result = await session.scalar(statement)

    return int(result or 0)


async def get_quota_status(
    session: AsyncSession,
    user_id: int,
    requests_limit_per_month: int,
) -> QuotaStatus:
    used = await get_requests_used_this_month(
        session=session,
        user_id=user_id,
    )

    remaining = max(
        requests_limit_per_month - used,
        0,
    )

    return QuotaStatus(
        limit=requests_limit_per_month,
        used=used,
        remaining=remaining,
        allowed=used < requests_limit_per_month,
    )
