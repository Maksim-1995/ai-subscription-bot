import pytest

from api_keys.models import ApiKey
from api_keys.services import (
    API_KEY_PREFIX,
    generate_api_key,
    hash_api_key,
)


@pytest.fixture
def user(django_user_model):
    """Создаёт пользователя для тестов."""

    return django_user_model.objects.create_user(
        username='test_user',
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
