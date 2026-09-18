from decimal import Decimal

from app.services.pricing import calculate_cost_usd


def test_calculate_openai_cost():
    cost = calculate_cost_usd(
        model='gpt-5.6-luna',
        prompt_tokens=1000,
        completion_tokens=500,
    )

    assert cost == Decimal('0.0008')
