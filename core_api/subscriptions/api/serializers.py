from rest_framework import serializers

from subscriptions.models import Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
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
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.all(),
        source='plan',
    )


class SubscriptionMeSerializer(serializers.Serializer):
    subscription = SubscriptionSerializer(
        allow_null=True,
        read_only=True,
    )
    usage = serializers.JSONField(
        allow_null=True,
        read_only=True,
    )