from django .urls import path
from webhooks.api.views import PaymentWebhookView


urlpatterns = [
    path(
        'payment/',
        PaymentWebhookView.as_view(),
        name='payment-webhook',
    ),
]
