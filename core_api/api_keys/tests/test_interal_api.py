from datetime import timedelta
from decimal import Decimal

import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from api_keys.services import generate_api_key
from subscriptions.models import Plan, Subscription


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
def test_validate_api_key_endpoint_success(
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

    client = APIClient()

    response = client.post(
        '/internal/api-keys/validate/',
        {
            'api_key': raw_api_key,
        },
        format='json',
        HTTP_X_INTERNAL_TOKEN=(
            settings.INTERNAL_API_TOKEN
        ),
    )

    assert response.status_code == status.HTTP_200_OK

    assert response.data['valid'] is True
    assert response.data['user_id'] == user.id
    assert response.data['plan'] == 'Pro'

    assert (
        response.data['requests_limit_per_month']
        == 1000
    )

    assert (
        response.data['subscription_status']
        == Subscription.Status.ACTIVE
    )


@pytest.mark.django_db
def test_validate_api_key_rejects_invalid_internal_token():
    client = APIClient()

    response = client.post(
        '/internal/api-keys/validate/',
        {
            'api_key': 'sk-live-anything',
        },
        format='json',
        HTTP_X_INTERNAL_TOKEN='wrong-token',
    )

    assert (
        response.status_code
        == status.HTTP_401_UNAUTHORIZED
    )

    assert response.data == {
        'valid': False,
        'reason': 'invalid_token',
    }


@pytest.mark.django_db
def test_validate_api_key_returns_not_found():
    client = APIClient()

    response = client.post(
        '/internal/api-keys/validate/',
        {
            'api_key': 'sk-live-does-not-exist',
        },
        format='json',
        HTTP_X_INTERNAL_TOKEN=(
            settings.INTERNAL_API_TOKEN
        ),
    )

    assert (
        response.status_code
        == status.HTTP_404_NOT_FOUND
    )

    assert response.data == {
        'valid': False,
        'reason': 'not_found',
    }
