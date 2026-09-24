from django.conf import settings
from django.db import models
from django.utils import timezone


class Plan(models.Model):
    """Тарифный план, который определяет цену и месячный лимит запросов."""

    name = models.CharField(
        max_length=100,
        unique=True,
    )
    requests_limit_per_month = models.PositiveIntegerField()
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    trial_days = models.PositiveSmallIntegerField(
        default=0
    )

    def __str__(self):
        """Вернуть название тарифа для админки и логов."""

        return self.name


class Subscription(models.Model):
    """Подписка пользователя на конкретный тарифный план."""

    class Status(models.TextChoices):
        """Допустимые состояния жизненного цикла подписки."""

        TRIAL = 'trial', 'Trial'
        ACTIVE = 'active', 'Active'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name='subscriptions',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TRIAL,
    )
    started_at = models.DateTimeField(
        default=timezone.now,
    )
    expires_at = models.DateTimeField()

    def __str__(self):
        """Вернуть краткое описание подписки для админки."""

        return (
            f'{self.user} — {self.plan} '
            f'({self.status})'
        )
