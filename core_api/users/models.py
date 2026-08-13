from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Пользователь сервиса подписок."""

    telegram_id = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
    )
