from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Менеджер пользователей с авторизацией по email."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Создать пользователя с нормализованным email и хэшированным паролем."""

        if not email:
            raise ValueError('Email is required.')

        # Email является USERNAME_FIELD, поэтому приводим его к единому виду
        # до сохранения и перед проверками уникальности.
        email = self.normalize_email(email).lower()

        user = self.model(
            email=email,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_user(self, email, password=None, **extra_fields):
        """Создать обычного пользователя без staff/superuser прав."""

        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        return self._create_user(
            email=email,
            password=password,
            **extra_fields,
        )

    def create_superuser(self, email, password=None, **extra_fields):
        """Создать администратора и проверить обязательные флаги доступа."""

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')

        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(
            email=email,
            password=password,
            **extra_fields,
        )


class User(AbstractUser):
    """Пользователь сервиса с email вместо username.

    `telegram_id` нужен для будущей связки аккаунта с Telegram-ботом.
    Поле может быть пустым, пока пользователь не прошёл привязку.
    """

    username = None

    email = models.EmailField(
        unique=True,
    )

    telegram_id = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # noqa: RUF012

    objects = UserManager()

    def __str__(self):
        """Вернуть email как человекочитаемое представление пользователя."""

        return self.email
