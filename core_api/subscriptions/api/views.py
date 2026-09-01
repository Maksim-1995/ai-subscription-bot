from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from subscriptions.api.serializers import (
    SubscribeSerializer,
    SubscriptionSerializer,
    SubscriptionMeSerializer
)
from subscriptions.exceptions import (
    ActiveSubscriptionExistsError,
    NoCancellableSubscriptionError,
)
from subscriptions.services import (
    cancel_subscription,
    get_latest_subscription,
    subscribe,
)


class SubscribeView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = SubscribeSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        plan = serializer.validated_data['plan']

        try:
            subscription = subscribe(
                user=request.user,
                plan=plan,
            )
        except ActiveSubscriptionExistsError:
            return Response(
                {
                    'detail': (
                        'У пользователя уже есть '
                        'действующая подписка.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = SubscriptionSerializer(
            subscription,
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class CancelSubscriptionView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            subscription = cancel_subscription(
                user=request.user,
            )
        except NoCancellableSubscriptionError:
            return Response(
                {
                    'detail': (
                        'У пользователя нет '
                        'действующей подписки.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubscriptionSerializer(
            subscription,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class SubscriptionMeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        subscription = get_latest_subscription(
            user=request.user,
        )

        data = {
            'subscription': subscription,
            'usage': None,
        }

        serializer = SubscriptionMeSerializer(
            data,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
