class ApiKeyNotFoundError(Exception):
    """Активный API-ключ не найден."""


class SubscriptionNotActiveError(Exception):
    """У владельца ключа нет действующей подписки."""
