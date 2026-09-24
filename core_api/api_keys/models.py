from django.conf import settings
from django.db import models
from django.db.models import Q


class ApiKey(models.Model):
    """Хэшированный API-ключ пользователя для доступа к AI Gateway.

    Сырой ключ показывается пользователю только один раз при генерации.
    В базе хранится SHA-256 хэш, чтобы утечка БД не раскрывала ключи.
    """

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
        """Ограничения модели API-ключа."""

        constraints = [  # noqa: RUF012
            # Пользователь может иметь историю ключей, но активным должен
            # оставаться только один ключ.
            models.UniqueConstraint(
                fields=['user'],
                condition=Q(is_active=True),
                name='unique_active_api_key_per_user',
            ),
        ]

    def __str__(self):
        """Вернуть безопасное строковое представление без сырого ключа."""

        return f'API key #{self.pk} for {self.user}'
