import json
import logging

import httpx

from collections.abc import AsyncIterator
from app.core.config import settings
from app.core.openai import openai_http_client
from app.schemas.chat import ChatCompletionRequest
from app.schemas.provider import (
    ProviderResult,
    ProviderStreamChunk,
)
from app.services.exceptions import (
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


def prepare_openai_input(
    request: ChatCompletionRequest,
) -> tuple[str | None, list[dict[str, str]]]:
    system_messages: list[str] = []
    input_messages: list[dict[str, str]] = []

    for message in request.messages:
        if message.role == 'system':
            system_messages.append(message.content)
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


def build_openai_payload(
    request: ChatCompletionRequest,
    *,
    stream: bool = False,
) -> dict[str, object]:
    model = (
        request.model
        or settings.openai_model
    )

    instructions, input_messages = (
        prepare_openai_input(request)
    )

    payload: dict[str, object] = {
        'model': model,
        'input': input_messages,
        'max_output_tokens': request.max_tokens,
        'temperature': request.temperature,
        'store': False,
        'reasoning': {
            'effort': 'none',
        },
    }

    if instructions is not None:
        payload['instructions'] = instructions

    if stream:
        payload['stream'] = True

    return payload


def extract_output_text(data: dict) -> str:
    parts: list[str] = []

    for item in data.get('output', []):
        if item.get('type') != 'message':
            continue

        for content in item.get('content', []):
            if content.get('type') == 'output_text':
                parts.append(content.get('text', ''))

    return ''.join(parts)


async def create_openai_completion(
    request: ChatCompletionRequest,
) -> ProviderResult:
    model = request.model or settings.openai_model

    instructions, input_messages = prepare_openai_input(request)

    payload = build_openai_payload(
        request,
    )

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
        logger.warning(
            'OpenAI rate limit: status=%s',
            response.status_code,
        )
        raise ProviderRateLimitError

    if response.status_code >= 500:
        logger.error(
            'OpenAI unavailable: status=%s',
            response.status_code,
        )
        raise ProviderUnavailableError

    if response.status_code >= 400:
        try:
            error_data = response.json()
            message = (
                error_data
                .get('error', {})
                .get('message', 'Unknown OpenAI error')
            )
        except ValueError:
            message = 'Invalid error response from OpenAI'

        logger.warning(
            'OpenAI rejected request: status=%s message=%s',
            response.status_code,
            message,
        )

        raise ProviderRequestError(
            status_code=response.status_code,
            message=message,
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderUnavailableError from exc

    usage = data.get('usage') or {}

    return ProviderResult(
        provider='openai',
        model=data.get('model', model),
        text=extract_output_text(data),
        prompt_tokens=usage.get(
            'input_tokens',
            0,
        ),
        completion_tokens=usage.get(
            'output_tokens',
            0,
        ),
        stop_reason=data.get('status'),
    )
 

async def create_openai_stream(
    request: ChatCompletionRequest,
) -> AsyncIterator[ProviderStreamChunk]:
    model = (
        request.model
        or settings.openai_model
    )

    payload = build_openai_payload(
        request,
        stream=True,
    )

    try:
        async with openai_http_client.stream(
            'POST',
            '/v1/responses',
            headers={
                'Authorization': (
                    f'Bearer {settings.openai_api_key}'
                ),
                'Content-Type': 'application/json',
            },
            json=payload,
        ) as response:

            if response.status_code == 429:
                raise ProviderRateLimitError

            if response.status_code >= 500:
                raise ProviderUnavailableError

            if response.status_code >= 400:
                await response.aread()

                try:
                    error_data = response.json()

                    message = (
                        error_data
                        .get('error', {})
                        .get(
                            'message',
                            'Unknown OpenAI error',
                        )
                    )

                except ValueError:
                    message = (
                        'Invalid error response '
                        'from OpenAI'
                    )

                raise ProviderRequestError(
                    status_code=response.status_code,
                    message=message,
                )

            async for line in response.aiter_lines():
                if not line.startswith('data:'):
                    continue

                raw_data = line[5:].strip()

                if not raw_data:
                    continue

                try:
                    data = json.loads(
                        raw_data,
                    )

                except json.JSONDecodeError as exc:
                    raise (
                        ProviderUnavailableError
                    ) from exc

                event_type = data.get('type')

                if (
                    event_type
                    == 'response.output_text.delta'
                ):
                    text = data.get(
                        'delta',
                        '',
                    )

                    if text:
                        yield ProviderStreamChunk(
                            provider='openai',
                            model=model,
                            text=text,
                        )

                    continue

                if event_type in {
                    'response.completed',
                    'response.incomplete',
                }:
                    final_response = (
                        data.get('response')
                        or {}
                    )

                    usage = (
                        final_response.get('usage')
                        or {}
                    )

                    yield ProviderStreamChunk(
                        provider='openai',
                        model=final_response.get(
                            'model',
                            model,
                        ),
                        done=True,
                        prompt_tokens=usage.get(
                            'input_tokens',
                            0,
                        ),
                        completion_tokens=usage.get(
                            'output_tokens',
                            0,
                        ),
                        stop_reason=(
                            final_response.get(
                                'status',
                            )
                        ),
                    )

                    return

                if event_type in {
                    'error',
                    'response.failed',
                }:
                    raise ProviderUnavailableError

    except httpx.TimeoutException as exc:
        raise ProviderUnavailableError from exc

    except httpx.RequestError as exc:
        raise ProviderUnavailableError from exc
