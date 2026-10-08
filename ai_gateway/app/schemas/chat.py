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
    
    temperature: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
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


class AssistantMessage(BaseModel):
    role: Literal['assistant'] = 'assistant'
    content: str


class ChatChoice(BaseModel):
    index: int
    message: AssistantMessage
    finish_reason: str | None


class ChatUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class QuotaInfo(BaseModel):
    limit: int
    used: int
    remaining: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal['chat.completion'] = 'chat.completion'
    created: int
    model: str

    choices: list[ChatChoice]
    usage: ChatUsage

    quota: QuotaInfo
