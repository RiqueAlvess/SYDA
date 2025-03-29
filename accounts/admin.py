from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User
from clients.models import Client

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Configuração do Admin para o modelo de usuário personalizado."""
    
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Informações pessoais"), {"fields": ("full_name", "position")}),
        (_("Cliente"), {"fields": ("client",)}),  # Adicionado campo client
        (_("Permissões"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Datas importantes"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "position", "client", "password1", "password2"),  # Adicionado client
        }),
    )
    list_display = ("email", "full_name", "position", "client", "is_staff")  # Adicionado client à exibição
    list_filter = ("is_staff", "is_active", "client")  # Adicionado filtro por client
    search_fields = ("email", "full_name", "position")
    ordering = ("email",)
    autocomplete_fields = ['client'] 
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Personaliza os campos de chave estrangeira no formulário"""
        if db_field.name == "client":
            kwargs["queryset"] = Client.objects.all().order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        """Adiciona lógica personalizada ao salvar"""
        # Garante que usuários novos tenham um cliente
        if not change and not obj.client: 
            default_client = Client.objects.first()
            if default_client:
                obj.client = default_client
        
        super().save_model(request, obj, form, change)

