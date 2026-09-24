from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),

    # Публичное API приложения.
    path('api/auth/', include('users.api.urls'),),
    path('api/subscriptions/', include('subscriptions.api.urls'),),
    path('api/keys/', include('api_keys.api.urls'),),

    # Внутренние и интеграционные endpoints должны быть закрыты на уровне
    # сети/reverse proxy в production-окружении.
    path('internal/api-keys/', include('api_keys.internal_api.urls'),),
    path('webhooks/', include('webhooks.api.urls'),),
]
