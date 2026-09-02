import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from api_keys.models import ApiKey
from api_keys.services import (
    API_KEY_PREFIX,
    hash_api_key,
)


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        email='user@example.com',
        password='StrongPassword123!',
    )


@pytest.fixture
def authenticated_client(user):
    client = APIClient()

    token = RefreshToken.for_user(user)

    client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {token.access_token}',
    )

    return client


@pytest.mark.django_db
def test_generate_api_key_success(
    authenticated_client,
    user,
):
    response = authenticated_client.post(
        '/api/keys/generate/',
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED

    assert 'api_key' in response.data

    raw_api_key = response.data['api_key']

    assert raw_api_key.startswith(API_KEY_PREFIX)

    api_key = ApiKey.objects.get(
        user=user,
        is_active=True,
    )

    assert api_key.key_hash == hash_api_key(
        raw_api_key,
    )


@pytest.mark.django_db
def test_generate_api_key_requires_authentication():
    client = APIClient()

    response = client.post(
        '/api/keys/generate/',
        format='json',
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED



@pytest.mark.django_db
def test_generate_api_key_does_not_expose_hash(
    authenticated_client,
):
    response = authenticated_client.post(
        '/api/keys/generate/',
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED

    assert 'key_hash' not in response.data



@pytest.mark.django_db
def test_generate_api_key_rotates_previous_key(
    authenticated_client,
    user,
):
    first_response = authenticated_client.post(
        '/api/keys/generate/',
        format='json',
    )

    first_raw_key = first_response.data['api_key']

    second_response = authenticated_client.post(
        '/api/keys/generate/',
        format='json',
    )

    second_raw_key = second_response.data['api_key']

    assert first_raw_key != second_raw_key

    assert ApiKey.objects.filter(
        user=user,
    ).count() == 2

    assert ApiKey.objects.filter(
        user=user,
        is_active=True,
    ).count() == 1
