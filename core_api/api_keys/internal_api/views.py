import hmac

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api_keys.exceptions import (
    ApiKeyNotFoundError,
    SubscriptionNotActiveError,
)
from api_keys.internal_api.serializers import (
    ApiKeyValidationResponseSerializer,
    ValidateApiKeySerializer,
)
from api_keys.services import validate_api_key


class ValidateApiKeyView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        internal_token = request.headers.get(
            'X-Internal-Token',
            '',
        )

        if not hmac.compare_digest(
            internal_token,
            settings.INTERNAL_API_TOKEN,
        ):
            return Response(
                {
                    'valid': False,
                    'reason': 'invalid_token',
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        request_serializer = ValidateApiKeySerializer(
            data=request.data,
        )
        request_serializer.is_valid(
            raise_exception=True,
        )

        raw_api_key = (
            request_serializer.validated_data['api_key']
        )

        try:
            api_key, subscription = validate_api_key(
                raw_api_key,
            )
        except ApiKeyNotFoundError:
            return Response(
                {
                    'valid': False,
                    'reason': 'not_found',
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except SubscriptionNotActiveError:
            return Response(
                {
                    'valid': False,
                    'reason': 'expired',
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        response_serializer = (
            ApiKeyValidationResponseSerializer(
                {
                    'valid': True,
                    'user_id': api_key.user_id,
                    'plan': subscription.plan.name,
                    'requests_limit_per_month': (
                        subscription
                        .plan
                        .requests_limit_per_month
                    ),
                    'requests_used_this_month': None,
                    'subscription_status': (
                        subscription.status
                    ),
                },
            )
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )
