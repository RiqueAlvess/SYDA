from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
from django.contrib.auth import get_user_model
from clients.models import Client

User = get_user_model()

class EmployeeCredentials(models.Model):
    """Credenciais para API de funcionários"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name=_("Cliente"))
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Usuário"))
    company = models.CharField(_("Empresa"), max_length=255)
    code = models.CharField(_("Código"), max_length=255)
    key = models.CharField(_("Chave"), max_length=255)
    
    # Status checkboxes
    is_active = models.BooleanField(_("Ativo"), default=False)
    is_inactive = models.BooleanField(_("Inativo"), default=False)
    is_away = models.BooleanField(_("Afastado"), default=False)
    is_pending = models.BooleanField(_("Pendente"), default=False)
    is_vacation = models.BooleanField(_("Férias"), default=False)
    
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)
    
    class Meta:
        verbose_name = _("Credencial de Funcionário")
        verbose_name_plural = _("Credenciais de Funcionários")
        unique_together = ['client', 'user', 'company']
    
    def __str__(self):
        return f"{self.company} - {self.user.email}"

class AbsenceCredentials(models.Model):
    """Credenciais para API de absenteísmo"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name=_("Cliente"))
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Usuário"))
    main_company = models.CharField(_("Empresa Principal"), max_length=255)
    code = models.CharField(_("Código"), max_length=255)
    key = models.CharField(_("Chave"), max_length=255)
    work_company = models.CharField(_("Empresa Trabalho"), max_length=255)
    start_date = models.DateField(_("Data Início"))
    end_date = models.DateField(_("Data Fim"))
    
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)
    
    class Meta:
        verbose_name = _("Credencial de Absenteísmo")
        verbose_name_plural = _("Credenciais de Absenteísmo")
        unique_together = ['client', 'user', 'main_company', 'work_company']
    
    def __str__(self):
        return f"{self.main_company} - {self.work_company} - {self.user.email}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        from datetime import timedelta
        
        # Verificar se a data de fim é maior que a data de início
        if self.end_date < self.start_date:
            raise ValidationError(_("A data de fim deve ser maior que a data de início."))
        
        # Verificar se o intervalo é de no máximo 30 dias
        if (self.end_date - self.start_date) > timedelta(days=30):
            raise ValidationError(_("O intervalo entre as datas não pode ser maior que 30 dias."))

class SyncLog(models.Model):
    """Log de sincronização com APIs externas"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name=_("Cliente"))
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Usuário"))
    api_type = models.CharField(_("Tipo de API"), max_length=50, 
                               choices=[('employee', 'Funcionários'), ('absence', 'Absenteísmo')])
    company = models.CharField(_("Empresa"), max_length=255)
    status = models.CharField(_("Status"), max_length=50, 
                             choices=[('success', 'Sucesso'), ('error', 'Erro'), ('partial', 'Parcial')])
    records_processed = models.IntegerField(_("Registros Processados"), default=0)
    records_success = models.IntegerField(_("Registros com Sucesso"), default=0)
    records_error = models.IntegerField(_("Registros com Erro"), default=0)
    error_message = models.TextField(_("Mensagem de Erro"), blank=True, null=True)
    start_time = models.DateTimeField(_("Hora Início"))
    end_time = models.DateTimeField(_("Hora Fim"), blank=True, null=True)
    task_id = models.CharField(_("ID da Tarefa"), max_length=36, blank=True, null=True)  
    
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Log de Sincronização")
        verbose_name_plural = _("Logs de Sincronização")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_api_type_display()} - {self.company} - {self.get_status_display()}"