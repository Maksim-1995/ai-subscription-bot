"""Pydantic-схемы запроса и ответа публичного chat-completions API."""

from typing import Literal, Self

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)


class ChatMessage(BaseModel):
    """Сообщение диалога с допустимой ролью и непустой строкой содержимого."""

    role: Literal[
        'system',
        'user',
        'assistant',
    ]

    content: str = Field(
        min_length=1,
    )


class ChatCompletionRequest(BaseModel):
    """Параметры генерации и диалог с хотя бы одним сообщением пользователя.

    Ограничения длины и диапазонов проверяет Pydantic. Поддержку имени модели
    проверяет обработчик, а при ``model=None`` он использует модель из настроек.
    """

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
        """Отклонить диалог без роли ``user`` после проверки отдельных полей.

        Raises:
            ValueError: В диалоге нет ни одного сообщения пользователя.
        """

        if not any(
            message.role == 'user'
            for message in self.messages
        ):
            raise ValueError(
                'At least one user message is required.'
            )

        return self


class AssistantMessage(BaseModel):
    """Текст ответа с фиксированной ролью ``assistant``."""

    role: Literal['assistant'] = 'assistant'
    content: str


class ChatChoice(BaseModel):
    """Вариант ответа с индексом и причиной завершения, допускающей ``None``."""

    index: int
    message: AssistantMessage
    finish_reason: str | None


class ChatUsage(BaseModel):
    """Счётчики входных, выходных и суммарных токенов ответа.

    Соотношение счётчиков здесь не проверяется; их формирует обработчик.
    """

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class QuotaInfo(BaseModel):
    """Месячный лимит и расход с учётом текущего обработанного запроса."""

    limit: int
    used: int
    remaining: int


class ChatCompletionResponse(BaseModel):
    """Ответ API с результатом генерации, расходом токенов и состоянием квоты.

    Поле ``created`` содержит Unix-время, выставленное обработчиком Gateway.
    """

    id: str
    object: Literal['chat.completion'] = 'chat.completion'
    created: int
    model: str

    choices: list[ChatChoice]
    usage: ChatUsage

    quota: QuotaInfo
