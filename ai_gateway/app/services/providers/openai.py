import httpx

from app.core.config import settings
from app.core.openai import openai_http_client
from app.schemas.chat import ChatCompletionRequest
from app.schemas.provider import ProviderResult
from app.services.exceptions import (
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderUnavailableError,
)


def prepare_openai_input(
    request: ChatCompletionRequest,
) -> tuple[str | None, list[dict[str, str]]]:
    system_messages: list[str] = []
    input_messages: list[dict[str, str]] = []

    for message in request.messages:
        if message.role == 'system':
            system_messages.append(
                message.content,
            )
            continue

        input_messages.append(
            {
                'role': message.role,
                'content': message.content,
            }
        )

    instructions = (
        '\n\n'.join(system_messages)
        if system_messages
        else None
    )

    return instructions, input_messages


def extract_output_text(
    data: dict,
) -> str:
    parts: list[str] = []

    for item in data.get('output', []):
        if item.get('type') != 'message':
            continue

        for content in item.get('content', []):
            if content.get('type') == 'output_text':
                parts.append(
                    content.get('text', '')
                )

    return ''.join(parts)


async def create_openai_completion(
    request: ChatCompletionRequest,
) -> ProviderResult:
    model = (
        request.model
        or settings.openai_model
    )

    instructions, input_messages = (
        prepare_openai_input(request)
    )

    payload = {
        'model': model,
        'input': input_messages,
        'max_output_tokens': request.max_tokens,
        'store': False,
        'reasoning': {
            'effort': 'none',
        },
    }

    if instructions is not None:
        payload['instructions'] = instructions

    try:
        response = await openai_http_client.post(
            '/v1/responses',
            headers={
                'Authorization': (
                    f'Bearer {settings.openai_api_key}'
                ),
                'Content-Type': 'application/json',
            },
            json=payload,
        )

    except httpx.TimeoutException as exc:
        raise ProviderUnavailableError from exc

    except httpx.RequestError as exc:
        raise ProviderUnavailableError from exc

    if response.status_code == 429:
        raise ProviderRateLimitError

    if response.status_code >= 500:
        raise ProviderUnavailableError

    if response.status_code >= 400:
        raise ProviderRequestError

    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderUnavailableError from exc

    usage = data.get('usage') or {}

    return ProviderResult(
        provider='openai',
        model=data.get(
            'model',
            model,
        ),
        text=extract_output_text(data),
        prompt_tokens=usage.get(
            'input_tokens',
            0,
        ),
        completion_tokens=usage.get(
            'output_tokens',
            0,
        ),
        stop_reason=data.get(
            'status',
        ),
    )
