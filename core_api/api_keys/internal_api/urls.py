from django.urls import path

from api_keys.internal_api.views import ValidateApiKeyView


urlpatterns = [
    path(
        'validate/',
        ValidateApiKeyView.as_view(),
        name='validate-api-key',
    ),
]
