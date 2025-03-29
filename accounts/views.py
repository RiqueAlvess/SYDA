from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone

from .models import EmployeeCredentials, AbsenceCredentials, SyncLog
from .forms import EmployeeCredentialsForm, AbsenceCredentialsForm
from clients.models import Client
from clients.mixins import ClientQuerySetMixin  # Import adicionado


class ApiConfigView(LoginRequiredMixin, TemplateView):
    """View principal para configurações de API"""
    template_name = 'api_config/config.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Recuperar o cliente associado à requisição
        client = self.request.client
        # Se não houver cliente cadastrado, mostrar mensagem de erro
        if not client:
            messages.error(
                self.request,
                "Não há clientes cadastrados no sistema. Por favor, cadastre um cliente antes de continuar."
            )
            context.update({
                'no_clients': True,
                'active_tab': self.request.GET.get('tab', 'employee')
            })
            return context
        
        # Recuperar as credenciais existentes para o usuário atual e o cliente
        employee_credentials = EmployeeCredentials.objects.filter(
            user=self.request.user,
            client=client
        ).first()
        
        absence_credentials = AbsenceCredentials.objects.filter(
            user=self.request.user,
            client=client
        ).first()
        
        # Preparar formulários
        if employee_credentials:
            employee_form = EmployeeCredentialsForm(
                instance=employee_credentials,
                user=self.request.user,
                client=client
            )
        else:
            employee_form = EmployeeCredentialsForm(user=self.request.user, client=client)
        
        if absence_credentials:
            absence_form = AbsenceCredentialsForm(
                instance=absence_credentials,
                user=self.request.user,
                client=client
            )
        else:
            absence_form = AbsenceCredentialsForm(user=self.request.user, client=client)
        
        # Adicionar dados ao contexto
        context.update({
            'client': client,
            'employee_credentials': employee_credentials,
            'absence_credentials': absence_credentials,
            'employee_form': employee_form,
            'absence_form': absence_form,
            'active_tab': self.request.GET.get('tab', 'employee'),  # Tab ativa padrão é employee
            'no_clients': False
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        # Identificar qual formulário foi enviado
        form_type = request.POST.get('form_type')
        client = self.request.client  # Uso do cliente a partir da requisição
        
        # Verificar se existe pelo menos um cliente
        if not client:
            messages.error(
                request,
                "Não há clientes cadastrados no sistema. Por favor, cadastre um cliente antes de continuar."
            )
            return redirect('api_config')
        
        if form_type == 'employee':
            # Processar formulário de funcionários
            instance = EmployeeCredentials.objects.filter(
                user=request.user, client=client
            ).first()
            form = EmployeeCredentialsForm(
                request.POST, instance=instance, user=request.user, client=client
            )
            
            if form.is_valid():
                credential = form.save(commit=False)
                credential.client = client  # Garantir que o cliente seja definido
                credential.user = request.user  # Garantir que o usuário seja definido
                credential.save()
                messages.success(request, "Credenciais de funcionários salvas com sucesso!")
                return redirect(reverse('api_config') + '?tab=employee')
            
            # Se o formulário não for válido, renderizar a página novamente com os erros
            context = self.get_context_data()
            context['employee_form'] = form
            context['active_tab'] = 'employee'
            return render(request, self.template_name, context)
            
        elif form_type == 'absence':
            # Processar formulário de absenteísmo
            instance = AbsenceCredentials.objects.filter(
                user=request.user, client=client
            ).first()
            form = AbsenceCredentialsForm(
                request.POST, instance=instance, user=request.user, client=client
            )
            
            if form.is_valid():
                credential = form.save(commit=False)
                credential.client = client  # Garantir que o cliente seja definido
                credential.user = request.user  # Garantir que o usuário seja definido
                credential.save()
                messages.success(request, "Credenciais de absenteísmo salvas com sucesso!")
                return redirect(reverse('api_config') + '?tab=absence')
            
            # Se o formulário não for válido, renderizar a página novamente com os erros
            context = self.get_context_data()
            context['absence_form'] = form
            context['active_tab'] = 'absence'
            return render(request, self.template_name, context)
        
        # Se nenhum formulário válido for identificado, redirecionar para a página principal
        return redirect('api_config')


class SyncLogListView(LoginRequiredMixin, ClientQuerySetMixin, ListView):
    """View para listar logs de sincronização"""
    model = SyncLog
    template_name = 'api_config/sync_logs.html'
    context_object_name = 'logs'
    paginate_by = 20
    
    def get_queryset(self):
        client = self.request.client
        if client:
            return SyncLog.objects.filter(user=self.request.user, client=client).order_by('-created_at')
        else:
            return SyncLog.objects.filter(user=self.request.user).order_by('-created_at')


# Função para logout customizado
def custom_logout(request):
    from django.contrib.auth import logout
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


from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.views.generic import CreateView
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect


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
        
        # Associar usuário a um cliente baseado no domínio do email
        email_domain = user.email.split('@')[-1]
        
        # Tentar encontrar cliente existente com este domínio ou criar um novo
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
        
        # Obter o cliente associado ao usuário atual (não o primeiro cliente)
        client = self.request.client
        
        # Verificar se o usuário tem um cliente associado
        if not client:
            context['no_client'] = True
            return context
            
        # Adicionar contadores ao contexto
        if Employee is not None:
            context['total_employees'] = Employee.objects.filter(client=client).count()
            context['active_employees'] = Employee.objects.filter(client=client, situacao='ATIVO').count()
        
        return context
