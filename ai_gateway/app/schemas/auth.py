"""Данные проверки API-ключа и контекст авторизованного запроса."""

from pydantic import BaseModel


class ApiKeyValidationResult(BaseModel):
    """Результат проверки ключа, полученный из Core API или Redis-кеша.

    Поля контекста необязательны, поскольку ответ может описывать отказ.
    Их наличие при ``valid=True`` проверяет зависимость авторизации.
    """

    valid: bool
    user_id: int | None = None
    plan: str | None = None
    requests_limit_per_month: int | None = None
    requests_used_this_month: int | None = None
    subscription_status: str | None = None
    reason: str | None = None


class ApiKeyContext(BaseModel):
    """Проверенные данные пользователя и подписки для сервисов Gateway.

    Вместо исходного ключа хранится его хеш. Переданный Core API счётчик
    запросов необязателен; локальная квота вычисляется по журналу Gateway.
    """

    user_id: int
    api_key_hash: str

    plan: str
    requests_limit_per_month: int
    requests_used_this_month: int | None = None

    subscription_status: str
