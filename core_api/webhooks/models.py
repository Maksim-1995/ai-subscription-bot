from django.db import models


class FailedWebhook(models.Model):
    """Webhook, который не удалось доставить получателю."""

    event_json = models.JSONField()
    target_url = models.URLField()
    attempts = models.PositiveSmallIntegerField(
        default=0,
    )
    last_error = models.TextField(
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f'Failed webhook #{self.pk} to {self.target_url}'
