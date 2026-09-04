import hmac

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from subscriptions.exceptions import (
    InvalidSubscriptionTransitionError,
    SubscriptionNotFoundError,
)
from subscriptions.services import activate_subscription
from webhooks.api.serializers import PaymentWebhookSerializer


class PaymentWebhookView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        payment_token = request.headers.get(
            'X-Payment-Token',
            '',
        )

        if not hmac.compare_digest(
            payment_token,
            settings.PAYMENT_WEBHOOK_TOKEN,
        ):
            return Response(
                {
                    'detail': 'Invalid payment webhook token.',
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = PaymentWebhookSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            subscription = activate_subscription(
                subscription_id=(
                    serializer.validated_data[
                        'subscription_id'
                    ]
                ),
                expires_at=(
                    serializer.validated_data[
                        'expires_at'
                    ]
                ),
            )
        except SubscriptionNotFoundError:
            return Response(
                {
                    'detail': 'Subscription not found.',
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except InvalidSubscriptionTransitionError:
            return Response(
                {
                    'detail': (
                        'Subscription cannot be activated '
                        'from its current status.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                'status': 'ok',
                'subscription_id': subscription.id,
                'subscription_status': subscription.status,
            },
            status=status.HTTP_200_OK,
        )
