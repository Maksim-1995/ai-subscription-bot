from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.dependencies.auth import get_api_key_context
from app.schemas.auth import ApiKeyContext
from app.schemas.quota import QuotaStatus
from app.services.quota import get_quota_status
from app.services.exceptions import QuotaExceededError


async def get_quota(
    auth_context: Annotated[
        ApiKeyContext,
        Depends(get_api_key_context),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_session),
    ],
) -> QuotaStatus:
    return await get_quota_status(
        session=session,
        user_id=auth_context.user_id,
        requests_limit_per_month=(
            auth_context.requests_limit_per_month
        ),
    )


async def enforce_quota(
    auth_context: Annotated[
        ApiKeyContext,
        Depends(get_api_key_context),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_session),
    ],
) -> QuotaStatus:
    quota = await get_quota_status(
        session=session,
        user_id=auth_context.user_id,
        requests_limit_per_month=(
            auth_context.requests_limit_per_month
        ),
    )

    if not quota.allowed:
        raise QuotaExceededError(
            limit=quota.limit,
            used=quota.used,
        )

    return quota
