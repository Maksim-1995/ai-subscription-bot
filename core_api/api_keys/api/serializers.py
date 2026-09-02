from rest_framework import serializers


class GeneratedApiKeySerializer(serializers.Serializer):
    api_key = serializers.CharField(
        read_only=True,
    )
