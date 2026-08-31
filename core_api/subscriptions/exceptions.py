class ActiveSubscriptionExistsError(Exception):
    """У пользователя уже есть действующая подписка."""


class NoCancellableSubscriptionError(Exception):
    """У пользователя нет подписки, которую можно отменить."""
