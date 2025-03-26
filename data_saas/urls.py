from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from accounts.views import DashboardView
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

# View personalizada para a página inicial que redireciona usuários logados
class HomePageView(TemplateView):
    template_name = "index.html"
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    # Página inicial
    path("", HomePageView.as_view(), name="home"),
    # API de autenticação (Simple JWT)
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # Dashboards e páginas principais
    path("dashboard/", login_required(DashboardView.as_view()), name="dashboard"),
    # Configurações de API
    path("api/", include("api_config.urls")),
    # Gerenciamento de funcionários
    path("employees/", include("employees.urls")),
]


admin.site.site_header = "SYDA - Administração"
admin.site.site_title = "Administração SYDA"
admin.site.index_title = "Bem-vindo ao SYDA"