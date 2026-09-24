from django.db import models


class FailedWebhook(models.Model):
    """Webhook, который не удалось доставить получателю.

    Таблица нужна как простая замена очереди/retry dashboard: событие можно
    найти в админке и разобрать вручную.
    """

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
        """Вернуть краткое описание failed webhook для админки."""

        return f'Failed webhook #{self.pk} to {self.target_url}'
