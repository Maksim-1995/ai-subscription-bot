"""Общий формат результатов и потоковых фрагментов LLM-провайдеров."""

from pydantic import BaseModel


class ProviderResult(BaseModel):
    """Нормализованный ответ провайдера для кеша, API и расчёта стоимости.

    Счётчики кешированных входных токенов относятся к кешу провайдера,
    а не к Redis-кешу готовых ответов Gateway.
    """

    provider: str
    model: str

    text: str

    prompt_tokens: int
    completion_tokens: int

    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0

    stop_reason: str | None = None



class ProviderStreamChunk(BaseModel):
    """Фрагмент генерации либо событие завершения потока провайдера.

    Текст и счётчики могут отсутствовать в отдельном событии и тогда получают
    значения по умолчанию. ``fallback_used`` отмечает переход на резервный
    провайдер; схема сама не объединяет фрагменты и не суммирует usage.
    """

    provider: str
    model: str

    text: str = ''
    done: bool = False

    prompt_tokens: int = 0
    completion_tokens: int = 0

    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0

    stop_reason: str | None = None

    fallback_used: bool = False
