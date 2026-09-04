from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from subscriptions.exceptions import (
    ActiveSubscriptionExistsError,
    NoCancellableSubscriptionError,
    SubscriptionNotFoundError,
    InvalidSubscriptionTransitionError,
)
from subscriptions.models import Subscription


CURRENT_STATUSES = (
    Subscription.Status.TRIAL,
    Subscription.Status.ACTIVE,
)


@transaction.atomic
def subscribe(user, plan):
    """Создаёт trial-подписку пользователя на тариф."""

    type(user).objects.select_for_update().get(
        pk=user.pk,
    )

    has_current_subscription = Subscription.objects.filter(
        user=user,
        status__in=CURRENT_STATUSES,
    ).exists()

    if has_current_subscription:
        raise ActiveSubscriptionExistsError

    started_at = timezone.now()

    subscription = Subscription.objects.create(
        user=user,
        plan=plan,
        status=Subscription.Status.TRIAL,
        started_at=started_at,
        expires_at=(
            started_at
            + timedelta(days=plan.trial_days)
        ),
    )

    return subscription


@transaction.atomic
def cancel_subscription(user):
    """Отменяет текущую подписку пользователя."""

    type(user).objects.select_for_update().get(
        pk=user.pk,
    )

    subscription = (
        Subscription.objects
        .filter(
            user=user,
            status__in=CURRENT_STATUSES,
        )
        .order_by('-started_at')
        .first()
    )

    if subscription is None:
        raise NoCancellableSubscriptionError

    subscription.status = Subscription.Status.CANCELLED
    subscription.save(
        update_fields=['status'],
    )

    return subscription


def get_latest_subscription(user):
    """Возвращает последнюю подписку пользователя."""

    return (
        Subscription.objects
        .select_related('plan')
        .filter(user=user)
        .order_by('-started_at')
        .first()
    )


@transaction.atomic
def activate_subscription(
    subscription_id,
    expires_at,
):
    """Активирует подписку после успешной оплаты."""

    try:
        subscription = (
            Subscription.objects
            .select_for_update()
            .select_related('plan', 'user')
            .get(pk=subscription_id)
        )
    except Subscription.DoesNotExist as exc:
        raise SubscriptionNotFoundError from exc

    if subscription.status == Subscription.Status.ACTIVE:
        return subscription

    if subscription.status != Subscription.Status.TRIAL:
        raise InvalidSubscriptionTransitionError

    subscription.status = Subscription.Status.ACTIVE
    subscription.expires_at = expires_at

    subscription.save(
        update_fields=[
            'status',
            'expires_at',
        ],
    )

    return subscription