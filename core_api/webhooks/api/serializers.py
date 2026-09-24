from rest_framework import serializers


class PaymentWebhookSerializer(serializers.Serializer):
    """Входящий webhook от платёжной системы в тестовом формате."""

    event = serializers.ChoiceField(
        choices=('payment_succeeded',),
    )
    subscription_id = serializers.IntegerField(
        min_value=1,
    )
    expires_at = serializers.DateTimeField()
