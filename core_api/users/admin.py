from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Админка для модели пользователя."""
    ordering = ('email',)

    list_display = (
        'id',
        'email',
        'telegram_id',
        'is_staff',
        'is_active',
    )

    search_fields = (
        'email',
        'telegram_id',
    )

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'email',
                    'password',
                ),
            },
        ),
        (
            'Personal info',
            {
                'fields': (
                    'first_name',
                    'last_name',
                    'telegram_id',
                ),
            },
        ),
        (
            'Permissions',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                ),
            },
        ),
        (
            'Important dates',
            {
                'fields': (
                    'last_login',
                    'date_joined',
                ),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'password1',
                    'password2',
                ),
            },
        ),
    )
