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
from django.db.models import Count, Sum, Q, F, Value, CharField
from django.db.models.functions import TruncMonth, Coalesce
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

from clients.models import Client
from api_config.models import SyncLog, EmployeeCredentials, AbsenceCredentials
from .models import Employee, Absence
from .services import APIService
from .tasks import sync_employees_task, sync_absences_task


class EmployeeListView(LoginRequiredMixin, ListView):
    """View para listar funcionários"""
    model = Employee
    template_name = 'employees/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 20
    
    def get_queryset(self):
        # Obter o primeiro cliente (simplificação)
        client = Client.objects.first()
        
        queryset = Employee.objects.filter(client=client)
        
        # Filtrar por situação
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
        
        # Adicionar variáveis para filtros
        context['search'] = self.request.GET.get('search', '')
        context['situacao'] = self.request.GET.get('situacao', '')
        
        # Obter situações disponíveis
        client = Client.objects.first()
        situacoes = Employee.objects.filter(client=client).values_list('situacao', flat=True).distinct()
        context['situacoes_disponiveis'] = [s for s in situacoes if s]
        
        # Obter contagem por situação
        situacao_counts = {}
        for sit in situacoes:
            if sit:
                count = Employee.objects.filter(client=client, situacao=sit).count()
                situacao_counts[sit] = count
        
        context['situacao_counts'] = situacao_counts
        
        # Última sincronização
        ultimo_sync = SyncLog.objects.filter(
            client=client,
            api_type='employee',
            status='success'
        ).order_by('-created_at').first()
        
        context['last_sync'] = ultimo_sync
        context['total_employees'] = Employee.objects.filter(client=client).count()
        
        # Ativar menu
        context['active'] = 'employees'
        
        return context


class EmployeeDetailView(LoginRequiredMixin, DetailView):
    """View para detalhes de um funcionário"""
    model = Employee
    template_name = 'employees/employee_detail.html'
    context_object_name = 'employee'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obter absenteísmo relacionado ao funcionário
        employee = self.get_object()
        absences = Absence.objects.filter(employee=employee)
        context['absences'] = absences.order_by('-dt_inicio_atestado')
        
        # Ativar menu
        context['active'] = 'employees'
        
        return context


@method_decorator(cache_page(60 * 5), name='dispatch')  # Cache por 5 minutos
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ativar menu
        context['active'] = 'dashboard'
        
        # Obter o cliente do usuário (simplificação: usar o primeiro cliente)
        client = Client.objects.first()
        
        if not client:
            context['no_client'] = True
            return context
        
        # Recuperar dados de funcionários e absenteísmo
        employees = Employee.objects.filter(client=client)
        absences = Absence.objects.filter(client=client)
        
        # Amostragem para datasets muito grandes (opcional)
        if absences.count() > 10000:
            absences = absences.order_by('?')[:10000]  # Amostragem aleatória
            
        # Verificar se existem dados
        if not employees.exists() or not absences.exists():
            context['no_data'] = True
            # Adicionar dados básicos para contexto
            context['total_employees'] = employees.count()
            context['total_absences'] = absences.count()
            return context
        
        # --- Calcular métricas principais ---
        total_employees = employees.count()
        total_absences = absences.count()
        total_days_off = absences.aggregate(total=Coalesce(Sum('dias_afastados'), 0))['total'] or 0
        
        # Taxa de absenteísmo (simplificado: dias afastamento / (dias úteis * total funcionários))
        working_days_per_month = 22
        months_analyzed = max(1, len(absences.dates('dt_inicio_atestado', 'month', order='ASC')))
        absenteeism_rate = (total_days_off / (working_days_per_month * months_analyzed * total_employees)) * 100
        
        # Custo aproximado (usando salário mínimo como base)
        MIN_WAGE_BRAZIL = 1412.00  # Salário mínimo 2024
        AVG_WORK_HOURS_PER_MONTH = 176  # 8 horas x 22 dias
        HOURLY_RATE = MIN_WAGE_BRAZIL / AVG_WORK_HOURS_PER_MONTH
        total_hours_off = total_days_off * 8  # 8 horas por dia
        absenteeism_cost = total_hours_off * HOURLY_RATE
        
        # --- Gerar gráficos com Plotly ---
        
        # Definir paleta de cores
        color_palette = ['#1A5F7A', '#57C4E5', '#2E7D32', '#F57C00', '#8E24AA', 
                        '#D81B60', '#5E35B1', '#00ACC1', '#43A047',
                        '#E53935', '#6D4C41', '#1E88E5', '#00897B']
        
        # Configuração global de layout para economizar código
        layout_config = {
            'font': dict(family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"),
            'plot_bgcolor': 'white',
            'paper_bgcolor': 'white',
            'hoverlabel': dict(bgcolor="white", font_size=12),
            'margin': dict(l=5, r=5, t=5, b=5),
            'height': 350,
            'autosize': True
        }
        
        # 1. Gráfico de unidades com maior absenteísmo
        # Usar 'unidade' em vez de 'nome_unidade'
        units_data = absences.values('unidade')\
            .annotate(total_absences=Count('id'), 
                     total_days=Coalesce(Sum('dias_afastados'), 0))\
            .exclude(unidade__isnull=True)\
            .exclude(unidade__exact='')\
            .order_by('-total_days')[:10]
            
        # Converter para DataFrame para uso com Plotly
        units_df = pd.DataFrame(list(units_data))
        if not units_df.empty:
            units_df['unidade'] = units_df['unidade'].str.slice(0, 20) # Truncar nomes longos
            
            # Criar gráfico de barras horizontais
            fig_units = go.Figure()
            fig_units.add_trace(go.Bar(
                y=units_df['unidade'],
                x=units_df['total_days'],
                name='Dias Afastados',
                orientation='h',
                marker_color=color_palette[0]
            ))
            fig_units.add_trace(go.Bar(
                y=units_df['unidade'],
                x=units_df['total_absences'],
                name='Número de Atestados',
                orientation='h',
                marker_color=color_palette[1]
            ))
            
            fig_units.update_layout(
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis_title="Quantidade",
                **layout_config
            )
            
            # Converter para JSON
            units_chart = json.dumps(fig_units, cls=plotly.utils.PlotlyJSONEncoder)
        else:
            units_chart = None
            
        # 2. Gráfico de departamentos com maior absenteísmo
        # Usar 'setor' em vez de 'nome_setor'
        departments_data = absences.values('setor')\
            .annotate(total_absences=Count('id'), 
                     total_days=Coalesce(Sum('dias_afastados'), 0))\
            .exclude(setor__isnull=True)\
            .exclude(setor__exact='')\
            .order_by('-total_days')[:10]
            
        departments_df = pd.DataFrame(list(departments_data))
        if not departments_df.empty:
            # Criar gráfico de barras verticais
            fig_departments = go.Figure()
            fig_departments.add_trace(go.Bar(
                x=departments_df['setor'],
                y=departments_df['total_days'],
                name='Dias Afastados',
                marker_color=color_palette[2]
            ))
            fig_departments.add_trace(go.Bar(
                x=departments_df['setor'],
                y=departments_df['total_absences'],
                name='Número de Atestados',
                marker_color=color_palette[3]
            ))
            
            fig_departments.update_layout(
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis_title="Quantidade",
                **layout_config
            )
            
            # Converter para JSON
            departments_chart = json.dumps(fig_departments, cls=plotly.utils.PlotlyJSONEncoder)
        else:
            departments_chart = None
            
        # 3. Gráfico por CID
        cid_data = absences.values('grupo_patologico')\
            .annotate(total_absences=Count('id'), 
                     total_days=Coalesce(Sum('dias_afastados'), 0))\
            .exclude(grupo_patologico__isnull=True)\
            .exclude(grupo_patologico__exact='')\
            .order_by('-total_absences')[:10]
            
        cid_df = pd.DataFrame(list(cid_data))
        if not cid_df.empty:
            # Truncar nomes muito longos
            cid_df['grupo_patologico'] = cid_df['grupo_patologico'].str.slice(0, 30)
            
            # Criar gráfico de barras horizontais
            fig_cid = go.Figure()
            fig_cid.add_trace(go.Bar(
                y=cid_df['grupo_patologico'],
                x=cid_df['total_absences'],
                name='Número de Atestados',
                orientation='h',
                marker_color=color_palette[4]
            ))
            fig_cid.add_trace(go.Bar(
                y=cid_df['grupo_patologico'],
                x=cid_df['total_days'],
                name='Dias Afastados',
                orientation='h',
                marker_color=color_palette[5]
            ))
            
            fig_cid.update_layout(
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis_title="Quantidade",
                **layout_config
            )
            
            # Converter para JSON
            cid_chart = json.dumps(fig_cid, cls=plotly.utils.PlotlyJSONEncoder)
        else:
            cid_chart = None
            
        # 4. Gráfico por mês
        # Adicionar anotação para mês a partir da data de início
        absences_with_date = absences.filter(dt_inicio_atestado__isnull=False)
        month_data = absences_with_date.annotate(
                month=TruncMonth('dt_inicio_atestado')
            ).values('month')\
            .annotate(total_absences=Count('id'), 
                     total_days=Coalesce(Sum('dias_afastados'), 0))\
            .order_by('month')
            
        month_df = pd.DataFrame(list(month_data))
        if not month_df.empty and len(month_df) > 1:  # Verificar se há dados suficientes
            # Formatar datas para exibição
            month_df['month_str'] = month_df['month'].apply(lambda x: x.strftime('%m/%Y'))
            
            # Criar gráfico de linha com dois eixos Y
            fig_month = go.Figure()
            
            # Adicionar linhas
            fig_month.add_trace(go.Scatter(
                x=month_df['month_str'],
                y=month_df['total_days'],
                name='Dias Afastados',
                line=dict(color=color_palette[6], width=3),
                mode='lines+markers'
            ))
            
            fig_month.add_trace(go.Scatter(
                x=month_df['month_str'],
                y=month_df['total_absences'],
                name='Número de Atestados',
                line=dict(color=color_palette[7], width=3, dash='dot'),
                mode='lines+markers',
                yaxis='y2'
            ))
            
            # CORRIGIDO: Criar uma cópia do layout_config sem o margin para evitar duplicação
            month_layout = layout_config.copy()
            del month_layout['margin']  # Remover margin do layout padrão
            
            # Usar o layout modificado e adicionar o margin específico
            fig_month.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(
                    title=dict(text="Dias Afastados", font=dict(color=color_palette[6]))
                ),
                yaxis2=dict(
                    title=dict(text="Atestados", font=dict(color=color_palette[7])),
                    anchor="x",
                    overlaying="y",
                    side="right"
                ),
                **month_layout,
                margin=dict(l=5, r=50, t=5, b=5)  # Ajuste para o segundo eixo Y
            )
            
            # Converter para JSON
            month_chart = json.dumps(fig_month, cls=plotly.utils.PlotlyJSONEncoder)
        else:
            month_chart = None
            
        # 5. Gráfico por gênero
        gender_data = absences.values('sexo')\
            .annotate(total_absences=Count('id'), 
                     total_days=Coalesce(Sum('dias_afastados'), 0))
            
        gender_df = pd.DataFrame(list(gender_data))
        if not gender_df.empty:
            # Mapear valores numéricos para rótulos de gênero
            gender_map = {1: 'Masculino', 2: 'Feminino', None: 'Não informado'}
            gender_df['gender_label'] = gender_df['sexo'].map(gender_map)
            
            # Calcular percentuais
            total = gender_df['total_absences'].sum()
            gender_df['percentage'] = (gender_df['total_absences'] / total * 100).round(2)
            
            # Criar gráfico de pizza
            fig_gender = px.pie(
                gender_df, 
                values='total_absences',
                names='gender_label',
                color_discrete_sequence=[color_palette[8], color_palette[9], color_palette[10]],
                hole=0.4
            )
            
            fig_gender.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                **layout_config
            )
            
            fig_gender.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='%{label}<br>Quantidade: %{value}<br>Percentual: %{percent}'
            )
            
            # Converter para JSON
            gender_chart = json.dumps(fig_gender, cls=plotly.utils.PlotlyJSONEncoder)
            
            # Preparar dados para as tabelas de CID por gênero
            gender_cid_data = {}
            
            for gender in gender_df['sexo'].unique():
                if gender is not None:  # Ignorar valores nulos
                    top_cids = absences.filter(sexo=gender)\
                        .values('grupo_patologico')\
                        .annotate(count=Count('id'))\
                        .exclude(grupo_patologico__isnull=True)\
                        .exclude(grupo_patologico__exact='')\
                        .order_by('-count')[:5]
                    
                    if top_cids:
                        gender_label = gender_map.get(gender, 'Outro')
                        gender_cid_data[gender_label] = list(top_cids)
            
            context['gender_cid_data'] = gender_cid_data
        else:
            gender_chart = None
            
        # 6. Gráfico de custo por setor
        # Usar 'setor' em vez de 'nome_setor'
        cost_data = absences.values('setor')\
            .annotate(total_days=Coalesce(Sum('dias_afastados'), 0))\
            .exclude(setor__isnull=True)\
            .exclude(setor__exact='')\
            .order_by('-total_days')[:5]
            
        cost_df = pd.DataFrame(list(cost_data))
        if not cost_df.empty:
            # Calcular custo com base nas horas e valor hora
            cost_df['total_hours'] = cost_df['total_days'] * 8  # 8 horas por dia
            cost_df['total_cost'] = cost_df['total_hours'] * HOURLY_RATE
            
            # Criar gráfico de barras
            fig_cost = go.Figure(go.Bar(
                x=cost_df['setor'],
                y=cost_df['total_cost'],
                marker_color=color_palette[11],
                text=cost_df['total_cost'].apply(lambda x: f'R$ {x:.2f}'.replace('.', ',')),
                textposition='auto'
            ))
            
            fig_cost.update_layout(
                yaxis_title="Custo (R$)",
                yaxis=dict(tickprefix='R$ ', tickformat=',.2f'),
                **layout_config
            )
            
            # Converter para JSON
            cost_chart = json.dumps(fig_cost, cls=plotly.utils.PlotlyJSONEncoder)
        else:
            cost_chart = None
        
        # Adicionar ao contexto
        context.update({
            'total_employees': total_employees,
            'total_absences': total_absences,
            'total_days_off': total_days_off,
            'absenteeism_rate': round(absenteeism_rate, 2),
            'absenteeism_cost': round(absenteeism_cost, 2),
            'total_hours_off': total_hours_off,
            'hourly_rate': round(HOURLY_RATE, 2),
            
            # Gráficos
            'units_chart': units_chart,
            'departments_chart': departments_chart,
            'cid_chart': cid_chart,
            'month_chart': month_chart,
            'gender_chart': gender_chart,
            'cost_chart': cost_chart,
            
            # Projeções de economia
            'savings_10': round(absenteeism_cost * 0.1, 2),
            'savings_20': round(absenteeism_cost * 0.2, 2),
            'savings_30': round(absenteeism_cost * 0.3, 2),
        })
        
        return context


@login_required
def sync_employees(request):
    """View para sincronizar funcionários"""
    if request.method == 'POST':
        # Verificar se é uma requisição AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Obter o cliente (simplificação: uso do primeiro cliente)
        client = Client.objects.first()
        
        if not client:
            if is_ajax:
                return JsonResponse({'success': False, 'message': 'Nenhum cliente encontrado.'})
            else:
                return redirect('employee_list')
        
        # Verificar credenciais
        credentials = EmployeeCredentials.objects.filter(user=request.user, client=client).first()
        if not credentials:
            if is_ajax:
                return JsonResponse({
                    'success': False, 
                    'message': 'Credenciais não configuradas. Configure suas credenciais na seção de Configurações API.'
                })
            else:
                return redirect('api_config')
        
        # Criar log de sincronização
        sync_log = SyncLog.objects.create(
            client=client,
            user=request.user,
            api_type='employee',
            company=credentials.company,
            status='error',  # Será atualizado pelo task
            records_processed=0,
            records_success=0,
            records_error=0,
            start_time=timezone.now()
        )
        
        # Disparar task de sincronização
        task = sync_employees_task.delay(
            request.user.id,
            client.id,
            sync_log.id
        )
        
        # Atualizar log com o ID da tarefa
        sync_log.task_id = task.id
        sync_log.save()
        
        if is_ajax:
            return JsonResponse({
                'success': True, 
                'message': 'Sincronização iniciada com sucesso!',
                'sync_log_id': sync_log.id
            })
        else:
            return redirect('sync_logs')
    
    # Se não for POST, redirecionar para a lista
    return redirect('employee_list')


@login_required
def sync_absences(request):
    """View para sincronizar absenteísmos"""
    if request.method == 'POST':
        # Verificar se é uma requisição AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Obter o cliente (simplificação: uso do primeiro cliente)
        client = Client.objects.first()
        
        if not client:
            if is_ajax:
                return JsonResponse({'success': False, 'message': 'Nenhum cliente encontrado.'})
            else:
                return redirect('employee_list')
        
        # Verificar credenciais
        credentials = AbsenceCredentials.objects.filter(user=request.user, client=client).first()
        if not credentials:
            if is_ajax:
                return JsonResponse({
                    'success': False, 
                    'message': 'Credenciais não configuradas. Configure suas credenciais na seção de Configurações API.'
                })
            else:
                return redirect('api_config')
        
        # Criar log de sincronização
        sync_log = SyncLog.objects.create(
            client=client,
            user=request.user,
            api_type='absence',
            company=credentials.main_company,
            status='error',  # Será atualizado pelo task
            records_processed=0,
            records_success=0,
            records_error=0,
            start_time=timezone.now()
        )
        
        # Disparar task de sincronização
        task = sync_absences_task.delay(
            request.user.id,
            client.id,
            sync_log.id
        )
        
        # Atualizar log com o ID da tarefa
        sync_log.task_id = task.id
        sync_log.save()
        
        if is_ajax:
            return JsonResponse({
                'success': True, 
                'message': 'Sincronização iniciada com sucesso!',
                'sync_log_id': sync_log.id
            })
        else:
            return redirect('sync_logs')
    
    # Se não for POST, redirecionar para a lista
    return redirect('employee_list')


@login_required
def sync_status(request, sync_id):
    """API para verificar o status de uma sincronização"""
    sync_log = get_object_or_404(SyncLog, id=sync_id, user=request.user)
    
    # Verificar se já foi finalizado
    completed = sync_log.end_time is not None
    
    # Preparar dados básicos
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
    
    # Se finalizado, adicionar data de término
    if completed:
        data['end_time'] = sync_log.end_time.isoformat()
    
    return JsonResponse(data)


@login_required
def sync_details(request, sync_id):
    """API para obter detalhes de uma sincronização"""
    sync_log = get_object_or_404(SyncLog, id=sync_id, user=request.user)
    
    # Preparar dados para a resposta
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
        
        # Calcular duração
        duration = sync_log.end_time - sync_log.start_time
        minutes, seconds = divmod(duration.seconds, 60)
        data['duration'] = f"{minutes}m {seconds}s"
    
    return JsonResponse(data)


@login_required
def sync_delete(request, sync_id):
    """View para excluir um log de sincronização"""
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
    """View para parar uma sincronização em andamento"""
    if request.method == 'POST':
        sync_log = get_object_or_404(SyncLog, id=sync_id, user=request.user)
        
        # Verificar se a sincronização já foi concluída
        if sync_log.end_time:
            return JsonResponse({'success': False, 'message': 'Esta sincronização já foi concluída'})
        
        try:
            # Tentar revogar a tarefa, se o ID da tarefa estiver disponível
            if sync_log.task_id:
                from celery.task.control import revoke
                revoke(sync_log.task_id, terminate=True)
            
            # Atualizar o log como interrompido
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
    """API para obter dados de funcionários para o dashboard"""
    # Manter essa view para compatibilidade
    client = Client.objects.first()
    if not client:
        return JsonResponse([], safe=False)
    
    employees = Employee.objects.filter(client=client)
    employees_data = list(employees.values())
    return JsonResponse(employees_data, safe=False)


@login_required
def dashboard_absences_api(request):
    """API para obter dados de absenteísmo para o dashboard"""
    # Manter essa view para compatibilidade
    client = Client.objects.first()
    if not client:
        return JsonResponse([], safe=False)
    
    absences = Absence.objects.filter(client=client)
    absences_data = list(absences.values())
    return JsonResponse(absences_data, safe=False)