from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Сериализатор публичной регистрации пользователя."""

    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'password',
        )
        read_only_fields = (
            'id',
        )

    def validate_email(self, value):
        """Нормализовать email и запретить дубли без учёта регистра."""

        email = value.strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                'Пользователь с таким email уже существует.'
            )

        return email

    def create(self, validated_data):
        """Создать пользователя через кастомный manager, чтобы пароль хэшировался."""

        return User.objects.create_user(
            **validated_data,
        )
