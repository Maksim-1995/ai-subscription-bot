from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.api.urls'),),
    path('api/subscriptions/',include('subscriptions.api.urls'),),
    path('api/keys/', include('api_keys.api.urls'),),
    path('internal/api-keys/', include('api_keys.internal_api.urls'),),
]
