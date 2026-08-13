from django.conf import settings
from django.db import models
from django.db.models import Q


class ApiKey(models.Model):
    """API-ключ пользователя для доступа к AI Gateway."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_keys',
    )
    key_hash = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=Q(is_active=True),
                name='unique_active_api_key_per_user',
            ),
        ]

    def __str__(self):
        return f'API key #{self.pk} for {self.user}'
