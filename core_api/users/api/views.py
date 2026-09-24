from rest_framework import generics
from rest_framework.permissions import AllowAny

from users.api.serializers import RegisterSerializer


class RegisterView(generics.CreateAPIView):
    """Публичный endpoint для регистрации нового пользователя."""

    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)
