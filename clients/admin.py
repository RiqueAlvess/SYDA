from django.contrib import admin
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "subdomain", "paid_until", "on_trial", "created_on")
    search_fields = ("name", "subdomain")
    list_filter = ("on_trial",)
