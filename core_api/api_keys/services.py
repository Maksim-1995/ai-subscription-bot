import hashlib
import secrets

from django.db import transaction

from api_keys.models import ApiKey


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
