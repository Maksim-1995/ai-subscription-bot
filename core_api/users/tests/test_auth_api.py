import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient


User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_register_user_success(api_client):
    payload = {
        'email': 'user@example.com',
        'password': 'StrongPassword123!',
    }

    response = api_client.post(
        '/api/auth/register/',
        payload,
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['email'] == 'user@example.com'
    assert 'password' not in response.data

    user = User.objects.get(email='user@example.com')

    assert user.check_password('StrongPassword123!')


@pytest.mark.django_db
def test_register_user_duplicate_email(api_client):
    User.objects.create_user(
        email='user@example.com',
        password='StrongPassword123!',
    )

    response = api_client.post(
        '/api/auth/register/',
        {
            'email': 'user@example.com',
            'password': 'AnotherPassword123!',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_register_user_requires_email(api_client):
    response = api_client.post(
        '/api/auth/register/',
        {
            'password': 'StrongPassword123!',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_register_user_requires_password(api_client):
    response = api_client.post(
        '/api/auth/register/',
        {
            'email': 'user@example.com',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_register_rejects_weak_password(api_client):
    response = api_client.post(
        '/api/auth/register/',
        {
            'email': 'user@example.com',
            'password': '123',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_register_user_duplicate_email(api_client):
    User.objects.create_user(
        email='user@example.com',
        password='StrongPassword123!',
    )

    response = api_client.post(
        '/api/auth/register/',
        {
            'email': 'user@example.com',
            'password': 'AnotherPassword123!',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'email' in response.data


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        email='user@example.com',
        password='StrongPassword123!',
    )


@pytest.mark.django_db
def test_login_success(api_client, user):
    response = api_client.post(
        '/api/auth/login/',
        {
            'email': 'user@example.com',
            'password': 'StrongPassword123!',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK

    assert 'access' in response.data
    assert 'refresh' in response.data


@pytest.mark.django_db
def test_login_wrong_password(api_client, user):
    response = api_client.post(
        '/api/auth/login/',
        {
            'email': 'user@example.com',
            'password': 'WrongPassword123!',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_login_unknown_user(api_client):
    response = api_client.post(
        '/api/auth/login/',
        {
            'email': 'unknown@example.com',
            'password': 'StrongPassword123!',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_refresh_token_success(api_client, user):
    login_response = api_client.post(
        '/api/auth/login/',
        {
            'email': 'user@example.com',
            'password': 'StrongPassword123!',
        },
        format='json',
    )

    refresh_token = login_response.data['refresh']

    response = api_client.post(
        '/api/auth/refresh/',
        {
            'refresh': refresh_token,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    assert 'access' in response.data


@pytest.mark.django_db
def test_refresh_token_invalid(api_client):
    response = api_client.post(
        '/api/auth/refresh/',
        {
            'refresh': 'invalid-token',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
