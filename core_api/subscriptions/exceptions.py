class ActiveSubscriptionExistsError(Exception):
    """У пользователя уже есть действующая подписка."""


class NoCancellableSubscriptionError(Exception):
    """У пользователя нет подписки, которую можно отменить."""


class SubscriptionNotFoundError(Exception):
    """Подписка не найдена."""


class InvalidSubscriptionTransitionError(Exception):
    """Попытка выполнить недопустимый переход состояния подписки."""
