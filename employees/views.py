import json
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Sum, Q, F
from django.db.models.functions import TruncMonth, Coalesce
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

from clients.models import Client
from api_config.models import SyncLog, EmployeeCredentials, AbsenceCredentials
from .models import Employee, Absence
from .services import APIService
from .tasks import sync_employees_task, sync_absences_task

# ============================================================
# Constantes para evitar duplicação de literais (S1192)
# ============================================================
DAYS_OFF_LABEL = "Dias Afastados"          # substitui duplicado 4x
NUM_ATTESTADOS_LABEL = "Número de Atestados"  # substitui duplicado 4x

class EmployeeListView(LoginRequiredMixin, ListView):
    """View para listar funcionários."""
    model = Employee
    template_name = 'employees/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 20
    
    def get_queryset(self):
        # Uso do primeiro cliente (simplificação)
        client = Client.objects.first()
        queryset = Employee.objects.filter(client=client)
        
        # Filtro por situacao
        situacao = self.request.GET.get('situacao')
        if situacao:
            queryset = queryset.filter(situacao=situacao)
        
        # Busca
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search) | 
                Q(matricula_funcionario__icontains=search) |
                Q(cpf__icontains=search)
            )
        
        # Ordenar por nome
        return queryset.order_by('nome')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['search'] = self.request.GET.get('search', '')
        context['situacao'] = self.request.GET.get('situacao', '')

        client = Client.objects.first()

        # Situações disponíveis
        situacoes = self._buscar_situacoes(client)
        context['situacoes_disponiveis'] = [s for s in situacoes if s]
        
        # Contagens por situacao
        context['situacao_counts'] = self._buscar_situacao_counts(client, situacoes)

        # Última sincronização de funcionários
        ultimo_sync = SyncLog.objects.filter(
            client=client,
            api_type='employee',
            status='success'
        ).order_by('-created_at').first()
        
        context['last_sync'] = ultimo_sync
        context['total_employees'] = Employee.objects.filter(client=client).count()
        
        # Ativar item no menu
        context['active'] = 'employees'
        
        return context
    
    def _buscar_situacoes(self, client):
        if not client:
            return []
        return Employee.objects.filter(client=client).values_list('situacao', flat=True).distinct()
    
    def _buscar_situacao_counts(self, client, situacoes):
        situacao_counts = {}
        for sit in situacoes:
            if sit:
                count = Employee.objects.filter(client=client, situacao=sit).count()
                situacao_counts[sit] = count
        return situacao_counts


class EmployeeDetailView(LoginRequiredMixin, DetailView):
    """View para detalhes de um funcionário."""
    model = Employee
    template_name = 'employees/employee_detail.html'
    context_object_name = 'employee'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.get_object()
        absences = Absence.objects.filter(employee=employee).order_by('-dt_inicio_atestado')
        context['absences'] = absences
        
        # Ativar item no menu
        context['active'] = 'employees'
        return context


@method_decorator(cache_page(60 * 5), name='dispatch')  # Cache de 5 minutos
class DashboardView(LoginRequiredMixin, TemplateView):
    """Exibe o dashboard principal de absenteísmo."""
    template_name = 'dashboard/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active'] = 'dashboard'
        
        client = Client.objects.first()
        if not client:
            context['no_client'] = True
            return context
        
        employees = Employee.objects.filter(client=client)
        absences = Absence.objects.filter(client=client)

        # Se não há dados de employees ou absences, retorna cedo
        if not self._verifica_dados_basicos(context, employees, absences):
            return context
        
        # Calcular métricas gerais
        (context['total_employees'],
         context['total_absences'],
         context['total_days_off'],
         absenteeism_rate,
         absenteeism_cost,
         total_hours_off,
         hourly_rate) = self._calcular_metricas_absenteismo(employees, absences)
        
        context['absenteeism_rate'] = round(absenteeism_rate, 2)
        context['absenteeism_cost'] = round(absenteeism_cost, 2)
        context['total_hours_off'] = total_hours_off
        context['hourly_rate'] = round(hourly_rate, 2)
        
        # Projeção de economia (10%, 20%, 30%)
        context['savings_10'] = round(absenteeism_cost * 0.1, 2)
        context['savings_20'] = round(absenteeism_cost * 0.2, 2)
        context['savings_30'] = round(absenteeism_cost * 0.3, 2)
        
        # Construir gráficos
        context['units_chart'] = self._build_units_chart(absences)
        context['departments_chart'] = self._build_departments_chart(absences)
        context['cid_chart'] = self._build_cid_chart(absences)
        context['month_chart'] = self._build_month_chart(absences)
        
        gender_chart, gender_cid_data = self._build_gender_chart(absences)
        context['gender_chart'] = gender_chart
        context['gender_cid_data'] = gender_cid_data
        
        context['cost_chart'] = self._build_cost_chart(absences, hourly_rate)
        
        return context
    
    # --------------------------------------
    # MÉTODOS AUXILIARES PARA get_context_data
    # --------------------------------------
    def _verifica_dados_basicos(self, context, employees, absences):
        """Se não existem registros de funcionários ou absences, define no_data e retorna False."""
        if not employees.exists() or not absences.exists():
            context['no_data'] = True
            context['total_employees'] = employees.count()
            context['total_absences'] = absences.count()
            return False
        return True
    
    def _calcular_metricas_absenteismo(self, employees, absences):
        """Calcula métricas principais de absenteísmo."""
        total_employees = employees.count()
        total_absences = absences.count()
        total_days_off = absences.aggregate(total=Coalesce(Sum('dias_afastados'), 0))['total'] or 0
        
        # Parâmetros simplificados
        working_days_per_month = 22
        months_analyzed = max(1, len(absences.dates('dt_inicio_atestado', 'month', order='ASC')))
        
        # Taxa de absenteísmo = dias_afastados / (dias_uteis * meses * total_func)
        absenteeism_rate = (total_days_off / (working_days_per_month * months_analyzed * total_employees)) * 100
        
        # Custo aproximado
        MIN_WAGE_BRAZIL = 1412.00
        AVG_WORK_HOURS_PER_MONTH = 176
        hourly_rate = MIN_WAGE_BRAZIL / AVG_WORK_HOURS_PER_MONTH
        total_hours_off = total_days_off * 8
        absenteeism_cost = total_hours_off * hourly_rate
        
        return (total_employees, total_absences, total_days_off,
                absenteeism_rate, absenteeism_cost, total_hours_off, hourly_rate)
    
    def _build_units_chart(self, absences):
        """Gráfico de unidades com maior absenteísmo."""
        units_data = (absences.values('unidade')
                      .annotate(total_absences=Count('id'),
                                total_days=Coalesce(Sum('dias_afastados'), 0))
                      .exclude(unidade__isnull=True)
                      .exclude(unidade__exact='')
                      .order_by('-total_days')[:10])
        if not units_data:
            return None
        
        df = pd.DataFrame(list(units_data))
        if df.empty:
            return None
        
        df['unidade'] = df['unidade'].str.slice(0, 20)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df['unidade'],
            x=df['total_days'],
            name=DAYS_OFF_LABEL,
            orientation='h'
        ))
        fig.add_trace(go.Bar(
            y=df['unidade'],
            x=df['total_absences'],
            name=NUM_ATTESTADOS_LABEL,
            orientation='h'
        ))
        fig.update_layout(barmode='group')
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    def _build_departments_chart(self, absences):
        """Gráfico de departamentos com maior absenteísmo."""
        departments_data = (absences.values('setor')
                            .annotate(total_absences=Count('id'),
                                      total_days=Coalesce(Sum('dias_afastados'), 0))
                            .exclude(setor__isnull=True)
                            .exclude(setor__exact='')
                            .order_by('-total_days')[:10])
        if not departments_data:
            return None
        
        df = pd.DataFrame(list(departments_data))
        if df.empty:
            return None
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df['setor'],
            y=df['total_days'],
            name=DAYS_OFF_LABEL
        ))
        fig.add_trace(go.Bar(
            x=df['setor'],
            y=df['total_absences'],
            name=NUM_ATTESTADOS_LABEL
        ))
        fig.update_layout(barmode='group')
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    def _build_cid_chart(self, absences):
        """Gráfico por CID / Grupo Patológico."""
        cid_data = (absences.values('grupo_patologico')
                    .annotate(total_absences=Count('id'),
                              total_days=Coalesce(Sum('dias_afastados'), 0))
                    .exclude(grupo_patologico__isnull=True)
                    .exclude(grupo_patologico__exact='')
                    .order_by('-total_absences')[:10])
        if not cid_data:
            return None
        
        df = pd.DataFrame(list(cid_data))
        if df.empty:
            return None
        
        df['grupo_patologico'] = df['grupo_patologico'].str.slice(0, 30)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df['grupo_patologico'],
            x=df['total_absences'],
            name=NUM_ATTESTADOS_LABEL,
            orientation='h'
        ))
        fig.add_trace(go.Bar(
            y=df['grupo_patologico'],
            x=df['total_days'],
            name=DAYS_OFF_LABEL,
            orientation='h'
        ))
        fig.update_layout(barmode='group')
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    def _build_month_chart(self, absences):
        """Gráfico de linhas por mês."""
        absences_with_date = absences.filter(dt_inicio_atestado__isnull=False)
        month_data = (absences_with_date.annotate(month=TruncMonth('dt_inicio_atestado'))
                      .values('month')
                      .annotate(total_absences=Count('id'),
                                total_days=Coalesce(Sum('dias_afastados'), 0))
                      .order_by('month'))
        
        if not month_data or len(month_data) <= 1:
            return None
        
        df = pd.DataFrame(list(month_data))
        if df.empty:
            return None
        
        df['month_str'] = df['month'].apply(lambda x: x.strftime('%m/%Y'))
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['month_str'],
            y=df['total_days'],
            name=DAYS_OFF_LABEL,
            mode='lines+markers'
        ))
        fig.add_trace(go.Scatter(
            x=df['month_str'],
            y=df['total_absences'],
            name=NUM_ATTESTADOS_LABEL,
            mode='lines+markers',
            yaxis='y2'
        ))
        
        fig.update_layout(
            yaxis2=dict(overlaying='y', side='right')
        )
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    def _build_gender_chart(self, absences):
        """Gráfico de distribuição de absenteísmo por gênero + top CIDs."""
        gender_data = (absences.values('sexo')
                       .annotate(total_absences=Count('id'),
                                 total_days=Coalesce(Sum('dias_afastados'), 0)))
        if not gender_data:
            return None, {}
        
        df = pd.DataFrame(list(gender_data))
        if df.empty:
            return None, {}
        
        gender_map = {1: 'Masculino', 2: 'Feminino', None: 'Não informado'}
        df['gender_label'] = df['sexo'].map(gender_map)
        
        total_abs = df['total_absences'].sum()
        df['percentage'] = (df['total_absences'] / total_abs * 100).round(2)
        
        fig_gender = px.pie(
            df,
            values='total_absences',
            names='gender_label',
            hole=0.4
        )
        fig_gender.update_traces(textposition='inside', textinfo='percent+label')
        
        gender_chart = json.dumps(fig_gender, cls=plotly.utils.PlotlyJSONEncoder)
        
        # Preparar top CIDs por gênero
        gender_cid_data = {}
        for gval in df['sexo'].unique():
            if gval is None:
                continue
            top_cids = (absences.filter(sexo=gval)
                        .values('grupo_patologico')
                        .annotate(count=Count('id'))
                        .exclude(grupo_patologico__isnull=True)
                        .exclude(grupo_patologico__exact='')
                        .order_by('-count')[:5])
            
            if top_cids:
                label = gender_map.get(gval, 'Outro')
                gender_cid_data[label] = list(top_cids)
        
        return gender_chart, gender_cid_data
    
    def _build_cost_chart(self, absences, hourly_rate):
        """Gráfico de custo por setor."""
        cost_data = (absences.values('setor')
                     .annotate(total_days=Coalesce(Sum('dias_afastados'), 0))
                     .exclude(setor__isnull=True)
                     .exclude(setor__exact='')
                     .order_by('-total_days')[:5])
        if not cost_data:
            return None
        
        df = pd.DataFrame(list(cost_data))
        if df.empty:
            return None
        
        df['total_hours'] = df['total_days'] * 8
        df['total_cost'] = df['total_hours'] * hourly_rate
        
        fig = go.Figure(go.Bar(
            x=df['setor'],
            y=df['total_cost'],
            text=df['total_cost'].apply(lambda x: f'R$ {x:.2f}'.replace('.', ',')),
            textposition='auto'
        ))
        fig.update_layout(yaxis=dict(tickprefix='R$ ', tickformat=',.2f'))
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


@login_required
def sync_employees(request):
    """View para sincronizar funcionários."""
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        client = Client.objects.first()
        
        if not client:
            if is_ajax:
                return JsonResponse({'success': False, 'message': 'Nenhum cliente encontrado.'})
            return redirect('employee_list')
        
        credentials = EmployeeCredentials.objects.filter(user=request.user, client=client).first()
        if not credentials:
            msg = 'Credenciais não configuradas. Configure suas credenciais na seção de Configurações API.'
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg})
            return redirect('api_config')
        
        sync_log = SyncLog.objects.create(
            client=client,
            user=request.user,
            api_type='employee',
            company=credentials.company,
            status='error',
            records_processed=0,
            records_success=0,
            records_error=0,
            start_time=timezone.now()
        )
        
        task = sync_employees_task.delay(request.user.id, client.id, sync_log.id)
        sync_log.task_id = task.id
        sync_log.save()
        
        if is_ajax:
            return JsonResponse({
                'success': True, 
                'message': 'Sincronização iniciada com sucesso!',
                'sync_log_id': sync_log.id
            })
        return redirect('sync_logs')
    
    return redirect('employee_list')


@login_required
def sync_absences(request):
    """View para sincronizar absenteísmo."""
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        client = Client.objects.first()
        
        if not client:
            if is_ajax:
                return JsonResponse({'success': False, 'message': 'Nenhum cliente encontrado.'})
            return redirect('employee_list')
        
        credentials = AbsenceCredentials.objects.filter(user=request.user, client=client).first()
        if not credentials:
            msg = 'Credenciais não configuradas. Configure suas credenciais na seção de Configurações API.'
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg})
            return redirect('api_config')
        
        sync_log = SyncLog.objects.create(
            client=client,
            user=request.user,
            api_type='absence',
            company=credentials.main_company,
            status='error',
            records_processed=0,
            records_success=0,
            records_error=0,
            start_time=timezone.now()
        )
        
        task = sync_absences_task.delay(request.user.id, client.id, sync_log.id)
        sync_log.task_id = task.id
        sync_log.save()
        
        if is_ajax:
            return JsonResponse({
                'success': True, 
                'message': 'Sincronização iniciada com sucesso!',
                'sync_log_id': sync_log.id
            })
        return redirect('sync_logs')
    
    return redirect('employee_list')


@login_required
def sync_status(request, sync_id):
    """API para verificar status de uma sincronização."""
    sync_log = get_object_or_404(SyncLog, id=sync_id, user=request.user)
    completed = sync_log.end_time is not None
    
    data = {
        'id': sync_log.id,
        'api_type': sync_log.api_type,
        'company': sync_log.company,
        'records_processed': sync_log.records_processed,
        'records_success': sync_log.records_success,
        'records_error': sync_log.records_error,
        'status': sync_log.status,
        'error_message': sync_log.error_message,
        'completed': completed
    }
    if completed:
        data['end_time'] = sync_log.end_time.isoformat()
    
    return JsonResponse(data)


@login_required
def sync_details(request, sync_id):
    """API para obter detalhes de uma sincronização."""
    sync_log = get_object_or_404(SyncLog, id=sync_id, user=request.user)
    
    data = {
        'id': sync_log.id,
        'api_type': sync_log.api_type,
        'api_type_display': sync_log.get_api_type_display(),
        'company': sync_log.company,
        'status': sync_log.status,
        'status_display': sync_log.get_status_display(),
        'records_processed': sync_log.records_processed,
        'records_success': sync_log.records_success,
        'records_error': sync_log.records_error,
        'error_message': sync_log.error_message,
        'start_time': sync_log.start_time.isoformat(),
    }
    if sync_log.end_time:
        data['end_time'] = sync_log.end_time.isoformat()
        duration = sync_log.end_time - sync_log.start_time
        minutes, seconds = divmod(duration.seconds, 60)
        data['duration'] = f"{minutes}m {seconds}s"
    
    return JsonResponse(data)


@login_required
def sync_delete(request, sync_id):
    """View para excluir um log de sincronização."""
    if request.method == 'POST':
        sync_log = get_object_or_404(SyncLog, id=sync_id, user=request.user)
        try:
            sync_log.delete()
            return JsonResponse({'success': True, 'message': 'Log excluído com sucesso'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Erro ao excluir: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)


@login_required
def sync_stop(request, sync_id):
    """View para parar uma sincronização em andamento."""
    if request.method == 'POST':
        sync_log = get_object_or_404(SyncLog, id=sync_id, user=request.user)
        
        if sync_log.end_time:
            return JsonResponse({'success': False, 'message': 'Esta sincronização já foi concluída'})
        
        try:
            if sync_log.task_id:
                from celery.task.control import revoke
                revoke(sync_log.task_id, terminate=True)
            
            sync_log.status = 'error'
            sync_log.end_time = timezone.now()
            sync_log.error_message = "Sincronização interrompida pelo usuário."
            sync_log.save()
            
            return JsonResponse({'success': True, 'message': 'Sincronização interrompida com sucesso'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Erro ao interromper: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)


@login_required
def dashboard_employees_api(request):
    """API para obter dados de funcionários para o dashboard (compatibilidade)."""
    client = Client.objects.first()
    if not client:
        return JsonResponse([], safe=False)
    
    employees = Employee.objects.filter(client=client)
    data = list(employees.values())
    return JsonResponse(data, safe=False)


@login_required
def dashboard_absences_api(request):
    """API para obter dados de absenteísmo para o dashboard (compatibilidade)."""
    client = Client.objects.first()
    if not client:
        return JsonResponse([], safe=False)
    
    absences = Absence.objects.filter(client=client)
    data = list(absences.values())
    return JsonResponse(data, safe=False)
