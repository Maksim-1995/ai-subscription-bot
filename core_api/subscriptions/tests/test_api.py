from decimal import Decimal

import pytest
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
def test_subscribe_success(
    authenticated_client,
    user,
    plan,
):
    response = authenticated_client.post(
        '/api/subscriptions/subscribe/',
        {
            'plan_id': plan.id,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED

    assert response.data['status'] == 'trial'

    assert response.data['plan']['id'] == plan.id
    assert response.data['plan']['name'] == 'Pro'

    assert Subscription.objects.filter(
        user=user,
        plan=plan,
        status=Subscription.Status.TRIAL,
    ).exists()


@pytest.mark.django_db
def test_subscribe_requires_authentication(plan):
    client = APIClient()

    response = client.post(
        '/api/subscriptions/subscribe/',
        {
            'plan_id': plan.id,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_subscribe_rejects_unknown_plan(
    authenticated_client,
):
    response = authenticated_client.post(
        '/api/subscriptions/subscribe/',
        {
            'plan_id': 999999,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_subscribe_requires_plan(
    authenticated_client,
):
    response = authenticated_client.post(
        '/api/subscriptions/subscribe/',
        {},
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert 'plan_id' in response.data


@pytest.mark.django_db
def test_subscribe_rejects_second_current_subscription(
    authenticated_client,
    plan,
):
    first_response = authenticated_client.post(
        '/api/subscriptions/subscribe/',
        {
            'plan_id': plan.id,
        },
        format='json',
    )

    assert (
        first_response.status_code
        == status.HTTP_201_CREATED
    )

    second_response = authenticated_client.post(
        '/api/subscriptions/subscribe/',
        {
            'plan_id': plan.id,
        },
        format='json',
    )

    assert (
        second_response.status_code
        == status.HTTP_400_BAD_REQUEST
    )

    assert Subscription.objects.count() == 1


@pytest.mark.django_db
def test_cancel_subscription_success(
    authenticated_client,
    user,
    plan,
):
    subscription = subscribe(
        user=user,
        plan=plan,
    )

    response = authenticated_client.post(
        '/api/subscriptions/cancel/',
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data['status'] == Subscription.Status.CANCELLED
    assert response.data['id'] == subscription.id
    assert response.data['plan']['id'] == plan.id
    subscription.refresh_from_db()

    assert subscription.status == Subscription.Status.CANCELLED


@pytest.mark.django_db
def test_cancel_subscription_requires_authentication():
    client = APIClient()

    response = client.post(
        '/api/subscriptions/cancel/',
        format='json',
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED



@pytest.mark.django_db
def test_cancel_without_subscription_returns_400(
    authenticated_client,
):
    response = authenticated_client.post(
        '/api/subscriptions/cancel/',
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_cancel_subscription_twice_returns_400(
    authenticated_client,
    user,
    plan,
):
    subscribe(
        user=user,
        plan=plan,
    )

    first_response = authenticated_client.post(
        '/api/subscriptions/cancel/',
        format='json',
    )

    assert first_response.status_code == status.HTTP_200_OK

    second_response = authenticated_client.post(
        '/api/subscriptions/cancel/',
        format='json',
    )

    assert second_response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_subscription_me_requires_authentication():
    client = APIClient()

    response = client.get(
        '/api/subscriptions/me/',
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_subscription_me_without_subscription(
    authenticated_client,
):
    response = authenticated_client.get(
        '/api/subscriptions/me/',
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data['subscription'] is None
    assert response.data['usage'] is None


@pytest.mark.django_db
def test_subscription_me_returns_subscription(
    authenticated_client,
    user,
    plan,
):
    subscription = subscribe(
        user=user,
        plan=plan,
    )

    response = authenticated_client.get(
        '/api/subscriptions/me/',
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.data['subscription']

    assert data['id'] == subscription.id
    assert data['status'] == Subscription.Status.TRIAL

    assert data['plan']['id'] == plan.id
    assert data['plan']['name'] == plan.name

    assert data['plan']['requests_limit_per_month'] == 1000

    assert response.data['usage'] is None


@pytest.mark.django_db
def test_subscription_me_returns_latest_subscription(
    authenticated_client,
    user,
    plan,
):
    first_subscription = subscribe(
        user=user,
        plan=plan,
    )

    cancel_subscription(user=user)

    second_subscription = subscribe(
        user=user,
        plan=plan,
    )

    response = authenticated_client.get(
        '/api/subscriptions/me/',
    )

    assert response.status_code == status.HTTP_200_OK

    assert (
        response.data['subscription']['id']
        == second_subscription.id
    )

    assert (
        response.data['subscription']['id']
        != first_subscription.id
    )
