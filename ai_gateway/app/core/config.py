from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = 'AI Gateway'
    app_debug: bool = False

    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str = '127.0.0.1'
    postgres_port: int = 5432
    postgres_schema: str = 'ai_gateway'

    redis_url: str

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    @property
    def database_url(self) -> str:
        return (
            'postgresql+asyncpg://'
            f'{self.postgres_user}:'
            f'{self.postgres_password}@'
            f'{self.postgres_host}:'
            f'{self.postgres_port}/'
            f'{self.postgres_db}'
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
