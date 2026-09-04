from decimal import Decimal

import pytest
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from subscriptions.models import Plan, Subscription
from subscriptions.services import subscribe, cancel_subscription


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


@pytest.fixture
def authenticated_client(user):
    client = APIClient()

    token = RefreshToken.for_user(user)

    client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {token.access_token}',
    )

    return client


@pytest.mark.django_db
def test_payment_succeeded_activates_subscription(
    user,
    plan,
):
    subscription = subscribe(
        user=user,
        plan=plan,
    )

    expires_at = timezone.now() + timedelta(days=30)

    client = APIClient()

    response = client.post(
        '/webhooks/payment/',
        {
            'event': 'payment_succeeded',
            'subscription_id': subscription.id,
            'expires_at': expires_at.isoformat(),
        },
        format='json',
        HTTP_X_PAYMENT_TOKEN=(
            settings.PAYMENT_WEBHOOK_TOKEN
        ),
    )

    assert response.status_code == status.HTTP_200_OK

    subscription.refresh_from_db()

    assert subscription.status == Subscription.Status.ACTIVE


@pytest.mark.django_db
def test_payment_webhook_rejects_invalid_token():
    client = APIClient()

    response = client.post(
        '/webhooks/payment/',
        {
            'event': 'payment_succeeded',
            'subscription_id': 1,
            'expires_at': timezone.now().isoformat(),
        },
        format='json',
        HTTP_X_PAYMENT_TOKEN='wrong-token',
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
