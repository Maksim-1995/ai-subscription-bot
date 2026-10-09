"""Расчёт стоимости в USD по тарифам и периодам, заданным в проекте."""

from datetime import datetime, timezone
from decimal import Decimal


# Цены заданы за миллион токенов. Decimal избегает погрешностей float
# при расчёте денежных сумм, а строковые литералы сохраняют исходные цены.
MILLION_TOKENS = Decimal('1000000')


MODEL_PRICING = {
    'gpt-5.6-luna': {
        'input': Decimal('0.20'),
        'output': Decimal('1.20'),
    },
}


DEEPSEEK_FLASH_PRICING = {
    'off_peak': {
        'cache_hit_input': Decimal('0.003'),
        'cache_miss_input': Decimal('0.15'),
        'output': Decimal('0.60'),
    },
    'peak': {
        'cache_hit_input': Decimal('0.006'),
        'cache_miss_input': Decimal('0.30'),
        'output': Decimal('1.20'),
    },
}


def is_deepseek_peak_time(
    now: datetime | None = None,
) -> bool:
    """Проверить пиковый период из настроенной в проекте тарифной схемы.

    Пиковые интервалы в будние дни: [01:00, 04:00) и [06:00, 10:00).
    Без аргумента используется текущее время UTC; переданное время
    проверяется в его часовом поясе без дополнительного преобразования.
    """
    now = now or datetime.now(timezone.utc)

    if now.weekday() >= 5:
        return False

    hour = now.hour

    return (
        1 <= hour < 4
        or 6 <= hour < 10
    )


def calculate_deepseek_cost_usd(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    prompt_cache_hit_tokens: int,
    prompt_cache_miss_tokens: int,
) -> Decimal:
    """Рассчитать стоимость DeepSeek с учётом кеша промпта и периода.

    Использовать тариф для текущего времени UTC. Входные токены,
    не учтённые в счётчиках кеша, оплатить по ставке cache miss.
    Вернуть сумму в USD, округлённую до шести знаков после запятой.
    """
    pricing_period = (
        'peak'
        if is_deepseek_peak_time()
        else 'off_peak'
    )

    pricing = DEEPSEEK_FLASH_PRICING[
        pricing_period
    ]

    known_prompt_tokens = (
        prompt_cache_hit_tokens
        + prompt_cache_miss_tokens
    )

    # Неполная разбивка кеша не должна уменьшать стоимость: неучтённый
    # остаток входных токенов считается cache miss по тарифам проекта.
    if known_prompt_tokens < prompt_tokens:
        prompt_cache_miss_tokens += (
            prompt_tokens
            - known_prompt_tokens
        )

    input_cache_hit_cost = (
        Decimal(prompt_cache_hit_tokens)
        / MILLION_TOKENS
        * pricing['cache_hit_input']
    )

    input_cache_miss_cost = (
        Decimal(prompt_cache_miss_tokens)
        / MILLION_TOKENS
        * pricing['cache_miss_input']
    )

    output_cost = (
        Decimal(completion_tokens)
        / MILLION_TOKENS
        * pricing['output']
    )

    return (
        input_cache_hit_cost
        + input_cache_miss_cost
        + output_cost
    ).quantize(
        Decimal('0.000001')
    )


def calculate_cost_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    *,
    provider: str = 'openai',
    prompt_cache_hit_tokens: int = 0,
    prompt_cache_miss_tokens: int = 0,
) -> Decimal:
    """Рассчитать стоимость токенов в USD по таблицам проекта.

    Для provider='deepseek' использовать тарифы кеша промпта и периода.
    Для остальных значений provider выбрать тариф из MODEL_PRICING
    по имени модели и сложить стоимость входных и выходных токенов.

    Raises:
        ValueError: Модель отсутствует в MODEL_PRICING при расчёте
            для провайдера, отличного от DeepSeek.
    """
    if provider == 'deepseek':
        return calculate_deepseek_cost_usd(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            prompt_cache_hit_tokens=(
                prompt_cache_hit_tokens
            ),
            prompt_cache_miss_tokens=(
                prompt_cache_miss_tokens
            ),
        )
    try:
        pricing = MODEL_PRICING[model]
    except KeyError as exc:
        raise ValueError(
            f'Pricing is not configured for model {model}.'
        ) from exc

    input_cost = (
        Decimal(prompt_tokens)
        * pricing['input']
        / MILLION_TOKENS
    )

    output_cost = (
        Decimal(completion_tokens)
        * pricing['output']
        / MILLION_TOKENS
    )

    return input_cost + output_cost


def is_supported_model(model: str) -> bool:
    """Проверить наличие модели в таблице MODEL_PRICING."""
    return model in MODEL_PRICING
