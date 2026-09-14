from pydantic import BaseModel


class ApiKeyValidationResult(BaseModel):
    valid: bool
    user_id: int | None = None
    plan: str | None = None
    requests_limit_per_month: int | None = None
    requests_used_this_month: int | None = None
    subscription_status: str | None = None
    reason: str | None = None


class ApiKeyContext(BaseModel):
    user_id: int
    api_key_hash: str

    plan: str
    requests_limit_per_month: int
    requests_used_this_month: int | None = None

    subscription_status: str
