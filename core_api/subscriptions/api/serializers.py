from rest_framework import serializers

from subscriptions.models import Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    """Представление тарифного плана в API."""

    class Meta:
        model = Plan
        fields = (
            'id',
            'name',
            'requests_limit_per_month',
            'price',
            'trial_days',
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    """Представление подписки вместе с вложенным тарифом."""

    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            'id',
            'status',
            'plan',
            'started_at',
            'expires_at',
        )


class SubscribeSerializer(serializers.Serializer):
    """Входные данные для оформления подписки на тариф."""

    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.all(),
        source='plan',
    )


class SubscriptionMeSerializer(serializers.Serializer):
    """Ответ endpoint'а с текущей подпиской и будущими usage-данными."""

    subscription = SubscriptionSerializer(
        allow_null=True,
        read_only=True,
    )
    usage = serializers.JSONField(
        allow_null=True,
        read_only=True,
    )
