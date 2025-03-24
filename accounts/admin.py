from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Configuração do Admin para o modelo de usuário personalizado."""
    
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Informações pessoais"), {"fields": ("full_name", "position")}),
        (_("Permissões"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Datas importantes"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "position", "password1", "password2"),
        }),
    )
    list_display = ("email", "full_name", "position", "is_staff")
    search_fields = ("email", "full_name", "position")
    ordering = ("email",)
