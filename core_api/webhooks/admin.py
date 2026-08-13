from django.contrib import admin

from webhooks.models import FailedWebhook


@admin.register(FailedWebhook)
class FailedWebhookAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'target_url',
        'attempts',
        'created_at',
    )
    readonly_fields = (
        'event_json',
        'target_url',
        'attempts',
        'last_error',
        'created_at',
    )
