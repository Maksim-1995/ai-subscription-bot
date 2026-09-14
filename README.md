# AI Subscription Bot

Сервис подписок с отдельным AI Gateway и будущим Telegram-ботом. Проект находится в активной разработке: часть Core API уже реализована, AI Gateway собирается вокруг FastAPI, а bot/infra пока остаются следующими этапами.

## Статус проекта

`WIP`: API, инфраструктура и структура сервисов могут меняться.

Что уже есть:

- `core_api` на Django/DRF: регистрация, JWT-login/refresh, подписки, генерация API-ключей, внутренний validate-key endpoint, payment webhook.
- `ai_gateway` на FastAPI: health-check, подключение к PostgreSQL/Redis, модель и Alembic-миграция `usage_log`, заготовка сервиса валидации API-ключей через Core API.
- `specs`: описание эндпоинтов и OpenAPI-спека Core API.
- pytest-тесты для основной бизнес-логики Core API.

Что еще в работе:

- публичный AI Gateway endpoint `POST /v1/chat/completions`;
- интеграция с LLM-провайдерами, fallback, streaming и кеширование ответов;
- Telegram-бот на aiogram;
- Dockerfile, docker-compose, Nginx и CI/CD.

## Архитектура

Плановая архитектура состоит из трех сервисов:

```text
Client / Telegram
      |
      v
Core API (Django/DRF) <--- internal HTTP ---> AI Gateway (FastAPI)
      |
      v
Telegram Bot (aiogram, webhook receiver)
```

Данные логически разделяются по сервисам. PostgreSQL может быть одним физическим инстансом, но каждый сервис должен владеть своими таблицами/схемой и не ходить напрямую в чужую бизнес-логику через ORM.

Ключевые решения из ТЗ:

- AI Gateway проверяет API-ключ через внутренний HTTP-запрос в Core API и кеширует результат в Redis.
- При недоступности Core API Gateway должен работать по стратегии `fail closed`: не пропускать запрос к AI-провайдеру без подтверждения ключа.
- Core API должен отправлять события в Telegram-бот через webhook с подписью и идемпотентностью.

## Стек

- Python 3.12
- Django, Django REST Framework, SimpleJWT
- FastAPI, SQLAlchemy async, Alembic
- PostgreSQL
- Redis
- Pytest, pytest-django, pytest-asyncio
- Планируется: aiogram, Docker Compose, Nginx, GitHub Actions

## Структура репозитория

```text
.
├── core_api/       # Django/DRF сервис подписок, пользователей и API-ключей
├── ai_gateway/     # FastAPI сервис для доступа к AI-провайдерам
├── bot/            # будущий Telegram-бот
├── infra/          # будущая инфраструктура: Nginx, compose, deploy
├── specs/          # API-спеки и описание эндпоинтов
└── docker-compose.yml
```

## Core API

Основные эндпоинты:

```text
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/refresh/

POST /api/subscriptions/subscribe/
POST /api/subscriptions/cancel/
GET  /api/subscriptions/me/

POST /api/keys/generate/

POST /internal/api-keys/validate/
POST /webhooks/payment/
```

Переменные окружения для локального запуска Core API описаны в `.env.example`. Django читает `.env` из директории `core_api/`, поэтому для нового окружения:

```bash
cd core_api
cp ../.env.example .env
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:8000
```

Важно: текущие настройки Core API ожидают PostgreSQL. Перед миграциями должен быть доступен PostgreSQL и создана схема, указанная в `POSTGRES_SCHEMA` (`core` по умолчанию).

## AI Gateway

Сейчас реализован технический фундамент:

- `GET /health` проверяет доступность PostgreSQL и Redis;
- таблица `ai_gateway.usage_log` описана SQLAlchemy-моделью и Alembic-миграцией;
- есть сервисная заготовка для проверки API-ключа через Core API с кешированием результата в Redis.

Локальный запуск:

```bash
cd ai_gateway
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Важно: для `GET /health` должны быть доступны PostgreSQL и Redis. Настройки берутся из `ai_gateway/.env`.

## Тесты и проверки

Core API:

```bash
cd core_api
uv run pytest
uv run ruff check .
```

AI Gateway:

```bash
cd ai_gateway
uv run pytest
uv run ruff check .
```

## Документация API

Дополнительные материалы:

- `specs/endpoints.md` - инвентаризация эндпоинтов;
- `specs/core-api.yaml` - OpenAPI-спека Core API;
- техническое задание проекта - отдельный документ в рабочем контексте.

## Безопасность

- Секреты не должны попадать в Git: реальные `.env` файлы не коммитятся.
- API-ключи пользователей хранятся в БД только в виде хэша.
- Внутренний endpoint `/internal/api-keys/validate/` защищается заголовком `X-Internal-Token`.
- Payment webhook защищается заголовком `X-Payment-Token`.
- В будущей инфраструктуре внутренние роуты должны быть закрыты снаружи через Docker-сеть/Nginx.

## Roadmap

- Завершить настройки AI Gateway для общения с Core API.
- Реализовать `POST /v1/chat/completions`.
- Добавить подсчет лимитов и запись usage-событий.
- Подключить Telegram-бот и webhook-события от Core API.
- Описать и собрать Docker-инфраструктуру.
- Добавить CI с lint/test jobs.
