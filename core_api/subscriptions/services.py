from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from subscriptions.exceptions import (
    ActiveSubscriptionExistsError,
    InvalidSubscriptionTransitionError,
    NoCancellableSubscriptionError,
    SubscriptionNotFoundError,
)
from subscriptions.models import Subscription

# Статусы, которые считаются текущей действующей подпиской.
CURRENT_STATUSES = (
    Subscription.Status.TRIAL,
    Subscription.Status.ACTIVE,
)


@transaction.atomic
def subscribe(user, plan):
    """Создать trial-подписку пользователя на тариф.

    У пользователя может быть только одна текущая подписка в статусе
    `trial` или `active`. Блокировка строки пользователя защищает от
    гонки, когда два запроса пытаются оформить подписку одновременно.
    """

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
    """Отменить последнюю текущую подписку пользователя.

    Отменять можно только подписки в статусе `trial` или `active`.
    Если такой подписки нет, вызывающий API-слой вернёт 400.
    """

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
    """Вернуть последнюю созданную подписку пользователя или `None`."""

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
    """Активировать trial-подписку после успешной оплаты.

    Повторная доставка одного и того же payment webhook не должна ломать
    состояние: уже активная подписка возвращается как есть.
    """

    try:
        subscription = (
            Subscription.objects
            .select_for_update()
            .select_related('plan', 'user')
            .get(pk=subscription_id)
        )
    except Subscription.DoesNotExist as exc:
        raise SubscriptionNotFoundError from exc

    # Идемпотентность нужна для webhook: платёжная система может прислать
    # одно и то же событие повторно.
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
