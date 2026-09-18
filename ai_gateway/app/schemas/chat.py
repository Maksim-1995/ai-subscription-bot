from typing import Literal, Self

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)


class ChatMessage(BaseModel):
    role: Literal[
        'system',
        'user',
        'assistant',
    ]

    content: str = Field(
        min_length=1,
    )


class ChatCompletionRequest(BaseModel):
    model: str | None = None

    messages: list[ChatMessage] = Field(
        min_length=1,
    )

    max_tokens: int = Field(
        default=512,
        ge=1,
        le=4096,
    )

    stream: bool = False

    @model_validator(mode='after')
    def validate_messages(self) -> Self:
        if not any(
            message.role == 'user'
            for message in self.messages
        ):
            raise ValueError(
                'At least one user message is required.'
            )

        return self
