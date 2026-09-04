from django.contrib import admin

from subscriptions.models import Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'requests_limit_per_month',
        'price',
        'trial_days',
    )

    search_fields = (
        'name',
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'plan',
        'status',
        'started_at',
        'expires_at',
    )

    list_filter = (
        'status',
        'plan',
    )

    search_fields = (
        'user__email',
        'plan__name',
    )

    list_select_related = (
        'user',
        'plan',
    )
