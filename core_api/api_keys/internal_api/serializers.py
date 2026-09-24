from rest_framework import serializers


class ValidateApiKeySerializer(serializers.Serializer):
    """Входные данные внутренней проверки API-ключа."""

    api_key = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )


class ApiKeyValidationResponseSerializer(serializers.Serializer):
    """Ответ Core API для AI Gateway после проверки ключа."""

    valid = serializers.BooleanField()
    user_id = serializers.IntegerField()
    plan = serializers.CharField()
    requests_limit_per_month = serializers.IntegerField()
    requests_used_this_month = serializers.IntegerField(
        allow_null=True,
    )
    subscription_status = serializers.CharField()
