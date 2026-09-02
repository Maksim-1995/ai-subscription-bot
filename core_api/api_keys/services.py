import hashlib
import secrets

from django.db import transaction
from django.utils import timezone

from api_keys.models import ApiKey
from api_keys.exceptions import (
    ApiKeyNotFoundError,
    SubscriptionNotActiveError,
)
from subscriptions.models import Subscription


API_KEY_PREFIX = 'sk-live-'


def hash_api_key(api_key: str) -> str:
    """Возвращает SHA-256 хэш API-ключа."""

    return hashlib.sha256(
        api_key.encode('utf-8'),
    ).hexdigest()


@transaction.atomic
def generate_api_key(user) -> tuple[ApiKey, str]:
    """Создаёт новый API-ключ пользователя.

    Все предыдущие активные ключи пользователя деактивируются.
    Сырой ключ возвращается только вызывающему коду и не сохраняется в БД.
    """

    ApiKey.objects.filter(
        user=user,
        is_active=True,
    ).update(is_active=False)

    raw_api_key = (
        f'{API_KEY_PREFIX}'
        f'{secrets.token_urlsafe(32)}'
    )

    api_key = ApiKey.objects.create(
        user=user,
        key_hash=hash_api_key(raw_api_key),
    )

    return api_key, raw_api_key


def validate_api_key(raw_api_key: str):
    """Проверяет API-ключ и право пользователя на доступ."""

    key_hash = hash_api_key(raw_api_key)

    api_key = (
        ApiKey.objects
        .select_related('user')
        .filter(
            key_hash=key_hash,
            is_active=True,
        )
        .first()
    )

    if api_key is None:
        raise ApiKeyNotFoundError

    subscription = (
        Subscription.objects
        .select_related('plan')
        .filter(
            user=api_key.user,
            status__in=(
                Subscription.Status.TRIAL,
                Subscription.Status.ACTIVE,
            ),
            expires_at__gt=timezone.now(),
        )
        .order_by('-started_at')
        .first()
    )

    if subscription is None:
        raise SubscriptionNotActiveError

    return api_key, subscription
