from datetime import timedelta
from decimal import Decimal

import pytest

from subscriptions.exceptions import (
    ActiveSubscriptionExistsError,
    NoCancellableSubscriptionError,
)
from subscriptions.models import Plan, Subscription
from subscriptions.services import (
    cancel_subscription,
    get_latest_subscription,
    subscribe,
)


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        email='user@example.com',
        password='StrongPassword123!',
    )


@pytest.fixture
def plan():
    return Plan.objects.create(
        name='Pro',
        requests_limit_per_month=1000,
        price=Decimal('999.00'),
        trial_days=14,
    )


@pytest.mark.django_db
def test_subscribe_creates_trial_subscription(
    user,
    plan,
):
    subscription = subscribe(
        user=user,
        plan=plan,
    )

    assert subscription.user == user
    assert subscription.plan == plan

    assert (
        subscription.status
        == Subscription.Status.TRIAL
    )

    assert Subscription.objects.count() == 1


@pytest.mark.django_db
def test_subscribe_sets_trial_expiration(
    user,
    plan,
):
    subscription = subscribe(
        user=user,
        plan=plan,
    )

    expected_expires_at = (
        subscription.started_at
        + timedelta(days=plan.trial_days)
    )

    assert (
        subscription.expires_at
        == expected_expires_at
    )