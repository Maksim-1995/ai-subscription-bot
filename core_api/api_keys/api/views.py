from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api_keys.api.serializers import GeneratedApiKeySerializer
from api_keys.services import generate_api_key


class GenerateApiKeyView(APIView):
    """Создание нового API-ключа для авторизованного пользователя."""

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        """Сгенерировать ключ и вернуть пользователю только его сырое значение."""

        _, raw_api_key = generate_api_key(
            user=request.user,
        )

        serializer = GeneratedApiKeySerializer(
            {
                'api_key': raw_api_key,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )
