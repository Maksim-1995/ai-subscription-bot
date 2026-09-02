from django.urls import path

from api_keys.api.views import GenerateApiKeyView


urlpatterns = [
    path('generate/',
            GenerateApiKeyView.as_view(),
            name='generate_api_key'
        ),
]
