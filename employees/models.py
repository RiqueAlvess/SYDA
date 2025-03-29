from django.db import models
from django.utils.translation import gettext_lazy as _
from clients.models import Client


class Employee(models.Model):
    """Modelo para armazenar dados de funcionários sincronizados da API"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name=_("Cliente"))

    # Campos da API (string-based removendo null=True)
    codigo_empresa = models.CharField(_("Código Empresa"), max_length=20, blank=True)
    nome_empresa = models.CharField(_("Nome Empresa"), max_length=200, blank=True)
    codigo = models.CharField(_("Código"), max_length=20)
    nome = models.CharField(_("Nome"), max_length=120)
    codigo_unidade = models.CharField(_("Código Unidade"), max_length=20, blank=True)
    nome_unidade = models.CharField(_("Nome Unidade"), max_length=130, blank=True)
    codigo_setor = models.CharField(_("Código Setor"), max_length=12, blank=True)
    nome_setor = models.CharField(_("Nome Setor"), max_length=130, blank=True)
    codigo_cargo = models.CharField(_("Código Cargo"), max_length=10, blank=True)
    nome_cargo = models.CharField(_("Nome Cargo"), max_length=130, blank=True)
    cbo_cargo = models.CharField(_("CBO Cargo"), max_length=10, blank=True)
    ccusto = models.CharField(_("Centro de Custo"), max_length=50, blank=True)
    nome_centro_custo = models.CharField(_("Nome Centro de Custo"), max_length=130, blank=True)
    matricula_funcionario = models.CharField(_("Matrícula"), max_length=30, blank=True)
    cpf = models.CharField(_("CPF"), max_length=19, blank=True)
    rg = models.CharField(_("RG"), max_length=19, blank=True)
    uf_rg = models.CharField(_("UF RG"), max_length=10, blank=True)
    orgao_emissor_rg = models.CharField(_("Órgão Emissor RG"), max_length=20, blank=True)
    situacao = models.CharField(_("Situação"), max_length=12, blank=True)
    sexo = models.IntegerField(_("Sexo"), blank=True, null=True)
    pis = models.CharField(_("PIS"), max_length=20, blank=True)
    ctps = models.CharField(_("CTPS"), max_length=30, blank=True)
    serie_ctps = models.CharField(_("Série CTPS"), max_length=25, blank=True)
    estado_civil = models.IntegerField(_("Estado Civil"), blank=True, null=True)
    tipo_contratacao = models.IntegerField(_("Tipo Contratação"), blank=True, null=True)
    data_nascimento = models.DateField(_("Data Nascimento"), blank=True, null=True)
    data_admissao = models.DateField(_("Data Admissão"), blank=True, null=True)
    data_demissao = models.DateField(_("Data Demissão"), blank=True, null=True)
    endereco = models.CharField(_("Endereço"), max_length=110, blank=True)
    numero_endereco = models.CharField(_("Número"), max_length=20, blank=True)
    bairro = models.CharField(_("Bairro"), max_length=80, blank=True)
    cidade = models.CharField(_("Cidade"), max_length=50, blank=True)
    uf = models.CharField(_("UF"), max_length=20, blank=True)
    cep = models.CharField(_("CEP"), max_length=10, blank=True)
    telefone_residencial = models.CharField(_("Telefone Residencial"), max_length=20, blank=True)
    telefone_celular = models.CharField(_("Telefone Celular"), max_length=20, blank=True)
    email = models.CharField(_("Email"), max_length=400, blank=True)
    deficiente = models.IntegerField(_("Deficiente"), blank=True, null=True)
    deficiencia = models.TextField(_("Deficiência"), blank=True, null=True)
    nome_mae = models.CharField(_("Nome da Mãe"), max_length=120, blank=True)
    data_ultima_alteracao = models.DateField(_("Data Última Alteração"), blank=True, null=True)
    matricula_rh = models.CharField(_("Matrícula RH"), max_length=30, blank=True)
    cor = models.IntegerField(_("Cor"), blank=True, null=True)
    escolaridade = models.IntegerField(_("Escolaridade"), blank=True, null=True)
    naturalidade = models.CharField(_("Naturalidade"), max_length=50, blank=True)
    ramal = models.CharField(_("Ramal"), max_length=10, blank=True)
    regime_revezamento = models.IntegerField(_("Regime Revezamento"), blank=True, null=True)
    regime_trabalho = models.CharField(_("Regime Trabalho"), max_length=500, blank=True)
    tel_comercial = models.CharField(_("Telefone Comercial"), max_length=20, blank=True)
    turno_trabalho = models.IntegerField(_("Turno Trabalho"), blank=True, null=True)
    rh_unidade = models.CharField(_("RH Unidade"), max_length=80, blank=True)
    rh_setor = models.CharField(_("RH Setor"), max_length=80, blank=True)
    rh_cargo = models.CharField(_("RH Cargo"), max_length=80, blank=True)
    rh_centro_custo_unidade = models.CharField(_("RH Centro Custo Unidade"), max_length=80, blank=True)

    # Campos de controle
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)

    def __str__(self):
        return f"{self.nome} ({self.matricula_funcionario or self.codigo})"

    class Meta:
        verbose_name = _("Funcionário")
        verbose_name_plural = _("Funcionários")
        unique_together = ['client', 'codigo']
        ordering = ['nome']


class Absence(models.Model):
    """Modelo para armazenar dados de absenteísmo sincronizados da API"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name=_("Cliente"))
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, verbose_name=_("Funcionário"),
        related_name='absences', blank=True, null=True
    )

    # Campos da API (string-based removendo null=True)
    unidade = models.CharField(_("Unidade"), max_length=130, blank=True)
    setor = models.CharField(_("Setor"), max_length=130, blank=True)
    matricula_func = models.CharField(_("Matrícula"), max_length=30, blank=True)
    dt_nascimento = models.DateField(_("Data Nascimento"), blank=True, null=True)
    sexo = models.IntegerField(_("Sexo"), blank=True, null=True)
    tipo_atestado = models.IntegerField(_("Tipo Atestado"), blank=True, null=True)
    dt_inicio_atestado = models.DateField(_("Data Início"), blank=True, null=True)
    dt_fim_atestado = models.DateField(_("Data Fim"), blank=True, null=True)
    hora_inicio_atestado = models.CharField(_("Hora Início"), max_length=5, blank=True)
    hora_fim_atestado = models.CharField(_("Hora Fim"), max_length=5, blank=True)
    dias_afastados = models.IntegerField(_("Dias Afastados"), blank=True, null=True)
    horas_afastado = models.CharField(_("Horas Afastado"), max_length=5, blank=True)
    cid_principal = models.CharField(_("CID Principal"), max_length=10, blank=True)
    descricao_cid = models.CharField(_("Descrição CID"), max_length=264, blank=True)
    grupo_patologico = models.CharField(_("Grupo Patológico"), max_length=80, blank=True)
    tipo_licenca = models.CharField(_("Tipo Licença"), max_length=100, blank=True)

    # Campos de controle
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)

    def __str__(self):
        employee_name = self.employee.nome if self.employee else f"Sem Matrícula ({self.matricula_func})"
        return f"{employee_name} - {self.dt_inicio_atestado} a {self.dt_fim_atestado}"

    class Meta:
        verbose_name = _("Absenteísmo")
        verbose_name_plural = _("Absenteísmos")
        ordering = ['-dt_inicio_atestado']
