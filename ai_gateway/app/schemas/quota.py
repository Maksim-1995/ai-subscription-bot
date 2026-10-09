"""Схема состояния месячной квоты запросов пользователя."""

from pydantic import BaseModel


class QuotaStatus(BaseModel):
    """Передать лимит, расход, остаток и решение о доступе между слоями.

    Сервис квот вычисляет значения; схема проверяет только их типы.
    """

    limit: int
    used: int
    remaining: int
    allowed: bool
