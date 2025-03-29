from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.views.generic import CreateView, TemplateView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.mixins import LoginRequiredMixin
from django_ratelimit.decorators import ratelimit
from clients.models import Client

from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.contrib.auth import logout


def custom_logout(request):
    logout(request)
    # Forçar limpeza da sessão
    request.session.flush()
    # Definir uma URL absoluta para evitar problemas de resolução
    return redirect('/')

# Importar modelo de funcionário, se o app employees estiver disponível
try:
    from employees.models import Employee
except ImportError:
    Employee = None

@method_decorator(csrf_protect, name="dispatch")
@method_decorator(ratelimit(key="ip", rate="5/m", method="POST"), name="post")
class CustomLoginView(LoginView):
    """View para login personalizada."""
    
    form_class = CustomAuthenticationForm
    template_name = "accounts/login.html"
    
    def dispatch(self, request, *args, **kwargs):
        # Redirecionar usuários já logados
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        remember_me = form.cleaned_data.get("remember_me", False)
        if not remember_me:
            # Configura a sessão para expirar quando o navegador for fechado
            self.request.session.set_expiry(0)
        return super().form_valid(form)

@method_decorator(csrf_protect, name="dispatch")
@method_decorator(ratelimit(key="ip", rate="3/m", method="POST"), name="post")
class SignUpView(CreateView):
    """View para registro personalizada."""
    
    form_class = CustomUserCreationForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("login")
    
    def dispatch(self, request, *args, **kwargs):
        # Redirecionar usuários já logados
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object
        
        # Associar usuário a um cliente - baseado no domínio do email ou outras regras
        email_domain = user.email.split('@')[-1]
        
        # Tentar encontrar cliente existente com este domínio ou criar um
        client, created = Client.objects.get_or_create(
            subdomain=email_domain.split('.')[0],
            defaults={
                'name': email_domain.split('.')[0].capitalize(),
            }
        )
        
        # Definir o cliente para este usuário
        user.client = client
        user.save()
        
        # Autenticar e fazer login do usuário após o registro
        email = form.cleaned_data.get("email")
        password = form.cleaned_data.get("password1")
        user = authenticate(username=email, password=password)
        login(self.request, user)
        return redirect("dashboard")

class DashboardView(LoginRequiredMixin, TemplateView):
    """View de dashboard protegida por login."""
    
    template_name = "dashboard/index.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obter o primeiro cliente (simplificação)
        client = Client.objects.first()
        
        # Adicionar contadores ao contexto
        if Employee is not None and client is not None:
            context['total_employees'] = Employee.objects.filter(client=client).count()
            context['active_employees'] = Employee.objects.filter(client=client, situacao='ATIVO').count()
        
        return context
