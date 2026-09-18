from decimal import Decimal


MILLION_TOKENS = Decimal('1000000')


MODEL_PRICING = {
    'gpt-5.6-luna': {
        'input': Decimal('0.20'),
        'output': Decimal('1.20'),
    },
}


def calculate_cost_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Decimal:
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
