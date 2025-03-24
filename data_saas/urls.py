from django.contrib import admin
from django.urls import path, include
from accounts.views import DashboardView
from django.contrib.auth.decorators import login_required
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    # API de autenticação (Simple JWT)
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # Dashboards e páginas principais
    path("dashboard/", login_required(DashboardView.as_view()), name="dashboard"),
    path("", login_required(DashboardView.as_view()), name="home"),
    # Configurações de API
    path("api/", include("api_config.urls")),
    # Gerenciamento de funcionários
    path("employees/", include("employees.urls")),
]

# Configura o admin para usar o site atual
admin.site.site_header = "SAAS de Dados - Administração"
admin.site.site_title = "Administração SAAS"
admin.site.index_title = "Bem-vindo ao Portal de Administração"