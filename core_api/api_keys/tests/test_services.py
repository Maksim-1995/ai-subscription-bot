import pytest

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from api_keys.exceptions import (
    ApiKeyNotFoundError,
    SubscriptionNotActiveError,
)
from api_keys.models import ApiKey
from api_keys.services import (
    API_KEY_PREFIX,
    generate_api_key,
    hash_api_key,
    validate_api_key,
)
from subscriptions.models import Plan, Subscription


@pytest.fixture
def user(django_user_model):
    """Создаёт пользователя для тестов."""

    return django_user_model.objects.create_user(
        email='test@example.com',
        password='StrongPassword123',
    )


@pytest.mark.django_db
def test_generate_api_key_has_expected_prefix(user):
    """Сгенерированный ключ имеет публичный префикс."""

    _, raw_api_key = generate_api_key(user)

    assert raw_api_key.startswith(API_KEY_PREFIX)


@pytest.mark.django_db
def test_generate_api_key_does_not_store_raw_key(user):
    """Сырой API-ключ не сохраняется в базе данных."""

    api_key, raw_api_key = generate_api_key(user)

    api_key.refresh_from_db()

    assert api_key.key_hash != raw_api_key


@pytest.mark.django_db
def test_generate_api_key_stores_correct_hash(user):
    """В БД сохраняется SHA-256 хэш сгенерированного ключа."""

    api_key, raw_api_key = generate_api_key(user)

    api_key.refresh_from_db()

    assert api_key.key_hash == hash_api_key(raw_api_key)


@pytest.mark.django_db
def test_generated_api_key_hash_has_sha256_length(user):
    """SHA-256 хэш содержит 64 hexadecimal-символа."""

    api_key, _ = generate_api_key(user)

    assert len(api_key.key_hash) == 64


@pytest.mark.django_db
def test_generate_api_key_deactivates_previous_key(user):
    """Новый ключ деактивирует предыдущий активный ключ."""

    first_api_key, _ = generate_api_key(user)
    second_api_key, _ = generate_api_key(user)

    first_api_key.refresh_from_db()
    second_api_key.refresh_from_db()

    assert first_api_key.is_active is False
    assert second_api_key.is_active is True


@pytest.mark.django_db
def test_user_has_only_one_active_api_key_after_rotation(user):
    """После ротации у пользователя остаётся один активный ключ."""

    generate_api_key(user)
    generate_api_key(user)
    generate_api_key(user)

    active_keys_count = ApiKey.objects.filter(
        user=user,
        is_active=True,
    ).count()

    assert active_keys_count == 1


@pytest.mark.django_db
def test_generate_api_key_keeps_key_history(user):
    """Ротация сохраняет старые ключи для истории."""

    generate_api_key(user)
    generate_api_key(user)

    assert ApiKey.objects.filter(user=user).count() == 2


@pytest.fixture
def plan():
    return Plan.objects.create(
        name='Pro',
        requests_limit_per_month=1000,
        price=Decimal('999.00'),
        trial_days=14,
    )


@pytest.mark.django_db
def test_validate_api_key_success(
    user,
    plan,
):
    _, raw_api_key = generate_api_key(user)

    Subscription.objects.create(
        user=user,
        plan=plan,
        status=Subscription.Status.ACTIVE,
        started_at=timezone.now(),
        expires_at=(
            timezone.now()
            + timedelta(days=30)
        ),
    )

    api_key, subscription = validate_api_key(
        raw_api_key,
    )

    assert api_key.user == user
    assert subscription.plan == plan


@pytest.mark.django_db
def test_validate_unknown_api_key_raises_error():
    with pytest.raises(ApiKeyNotFoundError):
        validate_api_key(
            'sk-live-invalid',
        )


@pytest.mark.django_db
def test_validate_inactive_api_key_raises_error(
    user,
    plan,
):
    _, first_raw_key = generate_api_key(user)

    generate_api_key(user)

    Subscription.objects.create(
        user=user,
        plan=plan,
        status=Subscription.Status.ACTIVE,
        started_at=timezone.now(),
        expires_at=(
            timezone.now()
            + timedelta(days=30)
        ),
    )

    with pytest.raises(ApiKeyNotFoundError):
        validate_api_key(first_raw_key)


@pytest.mark.django_db
def test_validate_api_key_rejects_expired_subscription(
    user,
    plan,
):
    _, raw_api_key = generate_api_key(user)

    Subscription.objects.create(
        user=user,
        plan=plan,
        status=Subscription.Status.ACTIVE,
        started_at=(
            timezone.now()
            - timedelta(days=60)
        ),
        expires_at=(
            timezone.now()
            - timedelta(days=30)
        ),
    )

    with pytest.raises(
        SubscriptionNotActiveError,
    ):
        validate_api_key(raw_api_key)
