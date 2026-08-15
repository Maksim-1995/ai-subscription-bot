# API Inventory (полный список эндпоинтов)

1. Core API (Django + DRF)
Публичные эндпоинты
1.1. Регистрация пользователя

    Метод/путь: POST /api/auth/register/

    Назначение: создание нового пользователя

    Публичный: да

    Аутентификация: нет

    Тело запроса (JSON):
    json

    {
      "username": "string",
      "password": "string",
      "email": "string (опционально)",
      "telegram_id": "number (опционально)"
    }

    Успешный ответ: 201 Created
    json

    {
      "access": "string (JWT)",
      "refresh": "string (JWT)"
    }

    Ошибки: 400 Bad Request (невалидные данные)

1.2. Вход пользователя

    Метод/путь: POST /api/auth/login/

    Назначение: получение JWT-токенов по username/password

    Публичный: да

    Аутентификация: нет

    Тело запроса:
    json

    {
      "username": "string",
      "password": "string"
    }

    Успешный ответ: 200 OK (та же структура, что в register)

    Ошибки: 401 Unauthorized

1.3. Обновление JWT-токена

    Метод/путь: POST /api/auth/refresh/

    Назначение: получить новый access-токен по refresh-токену

    Публичный: да

    Аутентификация: refresh-токен в теле

    Тело запроса:
    json

    {
      "refresh": "string"
    }

    Успешный ответ: 200 OK
    json

    {
      "access": "string",
      "refresh": "string (опционально, ротация)"
    }

    Ошибки: 401 Unauthorized

1.4. Оформление подписки

    Метод/путь: POST /api/subscriptions/subscribe/

    Назначение: создание новой подписки (со статусом trial, если план предусматривает trial_days)

    Публичный: да

    Аутентификация: JWT (access-токен в заголовке Authorization: Bearer <token>)

    Тело запроса:
    json

    {
      "plan_id": "number"
    }

    Успешный ответ: 201 Created с объектом подписки
    json

    {
      "id": 123,
      "plan": "pro",
      "status": "trial",
      "started_at": "2026-07-14T10:00:00Z",
      "expires_at": "2026-07-28T10:00:00Z"
    }

    Ошибки: 400 (неверный план, уже есть активная подписка), 401

1.5. Отмена подписки

    Метод/путь: POST /api/subscriptions/cancel/

    Назначение: отмена текущей активной/триальной подписки пользователя

    Публичный: да

    Аутентификация: JWT

    Тело запроса: пустое или необязательное

    Успешный ответ: 200 OK с обновлённым статусом (cancelled)

    Ошибки: 400 (нет активной подписки), 401

1.6. Получение информации о текущей подписке

    Метод/путь: GET /api/subscriptions/me/

    Назначение: вернуть текущую подписку, план, использование лимита (данные об использовании берутся из схемы AI Gateway)

    Публичный: да

    Аутентификация: JWT

    Тело запроса: нет

    Успешный ответ: 200 OK
    json

    {
      "subscription": {
        "status": "active",
        "plan": "pro",
        "expires_at": "2026-08-14T10:00:00Z"
      },
      "usage": {
        "requests_limit_per_month": 1000,
        "requests_used_this_month": 217
      }
    }

    Ошибки: 401, 404 (если нет подписки)

1.7. Генерация API-ключа

    Метод/путь: POST /api/keys/generate/

    Назначение: выпустить новый API-ключ для пользователя, старый деактивируется

    Публичный: да

    Аутентификация: JWT

    Тело запроса: нет

    Успешный ответ: 201 Created
    json

    {
      "api_key": "sk-live-xxxxx",
      "created_at": "2026-07-14T10:00:00Z"
    }

    (ключ показывается только один раз, в БД хранится только хэш)

    Ошибки: 401

1.8. Приёмник вебхука от платёжной песочницы

    Метод/путь: POST /webhooks/payment/

    Назначение: обработка события оплаты (подтверждение платежа, отмена и т.п.)

    Публичный: да (но должен проверять подпись/токен платёжной системы)

    Аутентификация: зависит от платёжной системы (например, заголовок X-Signature или секретный ключ)

    Тело запроса: формат платёжной системы (например, YooKassa/Stripe)
    json

    {
      "event": "payment_succeeded",
      "object": { ... }
    }

    Успешный ответ: 200 OK (подтверждение получения)

    Ошибки: 400 (неверная подпись), 500

Внутренние эндпоинты (недоступны снаружи docker-сети)
1.9. Валидация API-ключа для AI Gateway

    Метод/путь: POST /internal/api-keys/validate/

    Назначение: проверить API-ключ, вернуть данные о пользователе, тарифе и использовании

    Публичный: нет (только изнутри docker-сети)

    Аутентификация: заголовок X-Internal-Token: <shared secret из .env>

    Тело запроса:
    json

    {
      "api_key": "sk-live-xxxxx"
    }

    Успешный ответ: 200 OK
    json

    {
      "valid": true,
      "user_id": 42,
      "plan": "pro",
      "requests_limit_per_month": 1000,
      "requests_used_this_month": 217,
      "subscription_status": "active"
    }

    Ошибки:

        404 Not Found — если ключ не найден

        401 Unauthorized — если неверный X-Internal-Token или ключ неактивен/просрочен

        Тело ошибки: {"valid": false, "reason": "not_found" | "expired" | "invalid_token"}

    Дополнительно: время ответа должно быть ≤ 2 секунд (для таймаута в AI Gateway).

2. AI Gateway (FastAPI)
Публичные эндпоинты
2.1. Основной эндпоинт чат-комплитов

    Метод/путь: POST /v1/chat/completions

    Назначение: обработать запрос к LLM, вернуть ответ (или стримить его)

    Публичный: да (через Nginx)

    Аутентификация: API-ключ в заголовке Authorization: Bearer sk-live-... или X-API-Key: sk-live-... (выбрать формат, например, как у OpenAI)

    Тело запроса (OpenAI-совместимое):
    json

    {
      "model": "claude-3-5-sonnet",
      "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
      ],
      "temperature": 0.7,
      "stream": false
    }

    Успешный ответ (не стриминг): 200 OK
    json

    {
      "id": "chatcmpl-...",
      "object": "chat.completion",
      "created": 1234567890,
      "model": "claude-3-5-sonnet",
      "choices": [
        {
          "index": 0,
          "message": {"role": "assistant", "content": "..."},
          "finish_reason": "stop"
        }
      ],
      "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30
      }
    }

    Успешный ответ (стриминг): 200 OK с Content-Type: text/event-stream, чанки в формате SSE

    Ошибки:

        401 Unauthorized — неверный/отсутствующий API-ключ

        429 Too Many Requests — лимит исчерпан ({"error": "quota_exceeded"})

        503 Service Unavailable — Core API недоступен (fail closed)

        500 — ошибка провайдера после fallback

2.2. Health-check

    Метод/путь: GET /health

    Назначение: проверка доступности сервиса, Redis, БД, (опционально) провайдеров

    Публичный: да (но обычно не проксируется наружу или используется для мониторинга)

    Аутентификация: нет

    Тело запроса: нет

    Успешный ответ: 200 OK
    json

    {
      "status": "ok",
      "redis": true,
      "db": true,
      "providers": {"anthropic": true, "openai": true}
    }

    Ошибки: 503 при недоступности критичных компонентов

3. Telegram Bot (aiogram + aiohttp)
Публичные эндпоинты (на самом деле внутренние, но для бота это входящие вебхуки)
3.1. Приёмник событий от Core API

    Метод/путь: POST /webhooks/core-events

    Назначение: получить уведомление о событии (оплата, истечение подписки, предупреждение о квоте) и отправить сообщение пользователю в Telegram

    Публичный: нет (только внутри docker-сети)

    Аутентификация: подпись HMAC-SHA256 тела запроса в заголовке X-Signature

    Дополнительный заголовок: X-Event-Id: <uuid> для идемпотентности

    Тело запроса:
    json

    {
      "event": "payment_succeeded",
      "event_id": "uuid",
      "telegram_id": 123456789,
      "occurred_at": "2026-07-14T10:00:00Z",
      "data": {
        "plan": "pro",
        "expires_at": "2026-08-14"
      }
    }

    Успешный ответ: 200 OK (можно вернуть {"status": "ok"})

    Ошибки:

        401/403 — неверная подпись

        400 — неверный формат

        Повторная доставка того же event_id (если он уже обработан) должна игнорироваться с ответом 200 OK