from rest_framework import serializers


class GeneratedApiKeySerializer(serializers.Serializer):
    """Ответ с новым сырым API-ключом, который показывается только один раз."""

    api_key = serializers.CharField(
        read_only=True,
    )
