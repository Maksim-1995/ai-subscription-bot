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
