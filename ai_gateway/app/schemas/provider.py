from pydantic import BaseModel


class ProviderResult(BaseModel):
    provider: str
    model: str

    text: str

    prompt_tokens: int
    completion_tokens: int

    stop_reason: str | None = None
