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


@pytest.mark.django_db
def test_subscribe_rejects_second_current_subscription(
    user,
    plan,
):
    subscribe(
        user=user,
        plan=plan,
    )

    with pytest.raises(
        ActiveSubscriptionExistsError,
    ):
        subscribe(
            user=user,
            plan=plan,
        )

    assert Subscription.objects.count() == 1


@pytest.mark.django_db
def test_subscribe_allows_new_subscription_after_expired(
    user,
    plan,
):
    old_subscription = subscribe(
        user=user,
        plan=plan,
    )

    old_subscription.status = (
        Subscription.Status.EXPIRED
    )
    old_subscription.save(
        update_fields=['status'],
    )

    new_subscription = subscribe(
        user=user,
        plan=plan,
    )

    assert new_subscription.pk != old_subscription.pk

    assert Subscription.objects.count() == 2

    assert (
        new_subscription.status
        == Subscription.Status.TRIAL
    )


@pytest.mark.django_db
def test_cancel_subscription(user, plan):
    subscription = subscribe(
        user=user,
        plan=plan,
    )

    cancelled_subscription = cancel_subscription(
        user=user,
    )

    cancelled_subscription.refresh_from_db()

    assert (
        cancelled_subscription.status
        == Subscription.Status.CANCELLED
    )

    assert (
        cancelled_subscription.pk
        == subscription.pk
    )


@pytest.mark.django_db
def test_cancel_without_current_subscription_raises_error(
    user,
):
    with pytest.raises(
        NoCancellableSubscriptionError,
    ):
        cancel_subscription(user=user)


@pytest.mark.django_db
def test_get_latest_subscription(
    user,
    plan,
):
    first_subscription = subscribe(
        user=user,
        plan=plan,
    )

    first_subscription.status = (
        Subscription.Status.EXPIRED
    )
    first_subscription.save(
        update_fields=['status'],
    )

    second_subscription = subscribe(
        user=user,
        plan=plan,
    )

    result = get_latest_subscription(user)

    assert result == second_subscription


