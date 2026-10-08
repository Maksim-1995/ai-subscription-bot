from pydantic import BaseModel


class ProviderResult(BaseModel):
    provider: str
    model: str

    text: str

    prompt_tokens: int
    completion_tokens: int

    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0

    stop_reason: str | None = None



class ProviderStreamChunk(BaseModel):
    provider: str
    model: str

    text: str = ''
    done: bool = False

    prompt_tokens: int = 0
    completion_tokens: int = 0

    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0

    stop_reason: str | None = None

    fallback_used: bool = False
