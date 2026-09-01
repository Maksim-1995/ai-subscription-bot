from django.urls import path

from subscriptions.api.views import (
    CancelSubscriptionView,
    SubscribeView,
    SubscriptionMeView,
)


urlpatterns = [
    path(
        'subscribe/',
        SubscribeView.as_view(),
        name='subscribe',
    ),
    path(
        'cancel/',
        CancelSubscriptionView.as_view(),
        name='cancel',
    ),
    path(
        'me/',
        SubscriptionMeView.as_view(),
        name='me',
    ),
]
