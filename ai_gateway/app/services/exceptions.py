class CoreApiUnavailableError(Exception):
    """Core API недоступен для проверки API-ключа."""


class QuotaExceededError(Exception):
    """Месячная квота запросов исчерпана."""

    def __init__(
        self,
        limit: int,
        used: int,
    ):
        self.limit = limit
        self.used = used
        super().__init__('Monthly quota exceeded.')


class ProviderUnavailableError(Exception):
    """LLM-провайдер временно недоступен."""


class ProviderRateLimitError(Exception):
    """LLM-провайдер отклонил запрос из-за rate limit."""


class ProviderRequestError(Exception):
    """LLM-провайдер отклонил запрос как некорректный."""
    def __init__(
        self,
        status_code: int,
        message: str,
    ):
        self.status_code = status_code
        self.message = message

        super().__init__(
            f'Provider error {status_code}: {message}'
        )
