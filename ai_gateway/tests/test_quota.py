from unittest.mock import AsyncMock

import pytest

from app.services.quota import get_quota_status


@pytest.mark.asyncio
async def test_quota_allows_request():
    session = AsyncMock()

    session.scalar.return_value = 217

    quota = await get_quota_status(
        session=session,
        user_id=42,
        requests_limit_per_month=1000,
    )

    assert quota.limit == 1000
    assert quota.used == 217
    assert quota.remaining == 783
    assert quota.allowed is True


@pytest.mark.asyncio
async def test_quota_blocks_when_limit_reached():
    session = AsyncMock()

    session.scalar.return_value = 1000

    quota = await get_quota_status(
        session=session,
        user_id=42,
        requests_limit_per_month=1000,
    )

    assert quota.used == 1000
    assert quota.remaining == 0
    assert quota.allowed is False


@pytest.mark.asyncio
async def test_quota_remaining_never_negative():
    session = AsyncMock()

    session.scalar.return_value = 1005

    quota = await get_quota_status(
        session=session,
        user_id=42,
        requests_limit_per_month=1000,
    )

    assert quota.remaining == 0
    assert quota.allowed is False


@pytest.mark.asyncio
async def test_quota_for_new_user():
    session = AsyncMock()

    session.scalar.return_value = 0

    quota = await get_quota_status(
        session=session,
        user_id=42,
        requests_limit_per_month=1000,
    )

    assert quota.used == 0
    assert quota.remaining == 1000
    assert quota.allowed is True



