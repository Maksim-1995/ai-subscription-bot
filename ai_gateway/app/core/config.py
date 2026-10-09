"""Настройки Gateway из окружения и локального файла ``.env``."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Параметры приложения, подключений и внешних LLM-провайдеров.

    Поля без значений по умолчанию обязательны. Переменные окружения имеют
    приоритет над ``.env``; неизвестные поля файла игнорируются.
    """

    app_name: str = 'AI Gateway'
    app_debug: bool = False

    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str = '127.0.0.1'
    postgres_port: int = 5432
    postgres_schema: str = 'ai_gateway'

    redis_url: str
    response_cache_ttl_seconds:int = 600
    
    core_api_url: str
    internal_api_token: str

    openai_api_key: str
    openai_base_url: str = 'https://api.openai.com'
    openai_model: str = 'gpt-5.6-luna'
    openai_request_timeout: float = 60.0

    deepseek_api_key: str
    deepseek_base_url: str = 'https://api.deepseek.com'
    deepseek_model: str = 'deepseek-flash'
    deepseek_request_timeout: float = 60.0

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    @property
    def database_url(self) -> str:
        """Собрать URL PostgreSQL для асинхронного драйвера ``asyncpg``.

        Схема задаётся отдельно в SQLAlchemy-моделях и в URL не включается.
        Логин и пароль подставляются напрямую, без URL-кодирования.
        """

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
    """Вернуть кешированный экземпляр настроек текущего процесса.

    Повторные вызовы не перечитывают окружение до очистки кеша.
    При отсутствии обязательных полей Pydantic выдаёт ошибку валидации.
    """

    return Settings()


# Настройки валидируются уже при импорте модулей приложения.
settings = get_settings()
