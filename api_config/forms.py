from django import forms
from django.utils.translation import gettext_lazy as _
from .models import EmployeeCredentials, AbsenceCredentials
from datetime import datetime, timedelta

class EmployeeCredentialsForm(forms.ModelForm):
    """Formulário para credenciais de funcionários"""
    
    class Meta:
        model = EmployeeCredentials
        fields = ['company', 'code', 'key', 'is_active', 'is_inactive', 'is_away', 'is_pending', 'is_vacation']
        widgets = {
            'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da empresa'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código de acesso'}),
            'key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chave de API'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_inactive': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_away': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_pending': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_vacation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.client = kwargs.pop('client', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if self.client:
            instance.client = self.client
        if commit:
            instance.save()
        return instance

class AbsenceCredentialsForm(forms.ModelForm):
    """Formulário para credenciais de absenteísmo"""
    
    start_date = forms.DateField(
        label=_("Data Início"),
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'date',
            'required': 'required'
        }),
        input_formats=['%Y-%m-%d']  # Aceitar formato ISO
    )
    
    end_date = forms.DateField(
        label=_("Data Fim"),
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'date',
            'required': 'required'
        }),
        input_formats=['%Y-%m-%d']  # Aceitar formato ISO
    )
    
    class Meta:
        model = AbsenceCredentials
        fields = ['main_company', 'code', 'key', 'work_company', 'start_date', 'end_date']
        widgets = {
            'main_company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Empresa principal'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código de acesso'}),
            'key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chave de API'}),
            'work_company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Empresa de trabalho'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.client = kwargs.pop('client', None)
        super().__init__(*args, **kwargs)
        
        # Inicializar datas se estiver editando um registro existente
        if self.instance.pk:
            if self.instance.start_date:
                self.initial['start_date'] = self.instance.start_date.strftime('%Y-%m-%d')
            if self.instance.end_date:
                self.initial['end_date'] = self.instance.end_date.strftime('%Y-%m-%d')
        else:
            # Para novos registros, preencher com valores padrão
            today = datetime.now().date()
            self.initial['start_date'] = today.strftime('%Y-%m-%d')
            self.initial['end_date'] = (today + timedelta(days=7)).strftime('%Y-%m-%d')
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        
        if start_date and end_date:
            # Verificar se a data de fim é maior que a data de início
            if end_date < start_date:
                raise forms.ValidationError(_("A data de fim deve ser maior que a data de início."))
            
            # Verificar se o intervalo é de no máximo 30 dias
            if (end_date - start_date) > timedelta(days=30):
                raise forms.ValidationError(_("O intervalo entre as datas não pode ser maior que 30 dias."))
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if self.client:
            instance.client = self.client
        if commit:
            instance.save()
        return instance