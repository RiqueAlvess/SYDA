from django.contrib import admin
from .models import Employee, Absence

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'matricula_funcionario', 'cpf', 'nome_cargo', 'nome_unidade', 'situacao')
    list_filter = ('situacao', 'nome_empresa', 'nome_unidade', 'client')
    search_fields = ('nome', 'matricula_funcionario', 'cpf', 'email')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('client', 'codigo', 'nome', 'matricula_funcionario', 'cpf', 'situacao')
        }),
        ('Dados Profissionais', {
            'fields': ('codigo_empresa', 'nome_empresa', 'codigo_unidade', 'nome_unidade', 
                      'codigo_setor', 'nome_setor', 'codigo_cargo', 'nome_cargo', 'cbo_cargo',
                      'ccusto', 'nome_centro_custo')
        }),
        ('Dados Pessoais', {
            'fields': ('rg', 'uf_rg', 'orgao_emissor_rg', 'sexo', 'pis', 'ctps', 
                      'serie_ctps', 'estado_civil', 'tipo_contratacao', 'data_nascimento',
                      'data_admissao', 'data_demissao', 'nome_mae')
        }),
        ('Contato', {
            'fields': ('email', 'telefone_residencial', 'telefone_celular', 'tel_comercial', 'ramal')
        }),
        ('Endereço', {
            'fields': ('endereco', 'numero_endereco', 'bairro', 'cidade', 'uf', 'cep')
        }),
        ('Outros Dados', {
            'fields': ('deficiente', 'deficiencia', 'data_ultima_alteracao', 'matricula_rh',
                      'cor', 'escolaridade', 'naturalidade', 'regime_revezamento',
                      'regime_trabalho', 'turno_trabalho', 'rh_unidade', 'rh_setor',
                      'rh_cargo', 'rh_centro_custo_unidade')
        }),
        ('Controle', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(Absence)
class AbsenceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'dt_inicio_atestado', 'dt_fim_atestado', 'dias_afastados', 'cid_principal')
    list_filter = ('grupo_patologico', 'tipo_licenca', 'client')
    search_fields = ('employee__nome', 'employee__matricula_funcionario', 'cid_principal', 'descricao_cid')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('employee',)
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('client', 'employee', 'matricula_func')
        }),
        ('Período', {
            'fields': ('dt_inicio_atestado', 'dt_fim_atestado', 'hora_inicio_atestado', 
                      'hora_fim_atestado', 'dias_afastados', 'horas_afastado')
        }),
        ('Motivo', {
            'fields': ('tipo_atestado', 'cid_principal', 'descricao_cid', 
                      'grupo_patologico', 'tipo_licenca')
        }),
        ('Localização', {
            'fields': ('unidade', 'setor')
        }),
        ('Dados Adicionais', {
            'fields': ('dt_nascimento', 'sexo')
        }),
        ('Controle', {
            'fields': ('created_at', 'updated_at')
        }),
    )