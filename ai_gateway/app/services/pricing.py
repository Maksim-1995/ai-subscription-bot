from datetime import datetime, timezone
from decimal import Decimal


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
    return model in MODEL_PRICING
