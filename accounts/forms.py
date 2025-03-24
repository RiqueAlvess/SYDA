from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .validators import validate_corporate_email, validate_full_name

User = get_user_model()

class CustomAuthenticationForm(AuthenticationForm):
    """Formulário de login personalizado."""
    
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email"}),
        label="Email"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Senha"}),
        label="Senha"
    )

class CustomUserCreationForm(UserCreationForm):
    """Formulário de registro personalizado."""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email corporativo"}),
        label="Email",
        validators=[validate_corporate_email]
    )
    full_name = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Nome completo"}),
        label="Nome completo",
        validators=[validate_full_name]
    )
    position = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Cargo"}),
        label="Cargo"
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Senha", "id": "password1"}),
        label="Senha"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirme a senha"}),
        label="Confirme a senha"
    )
    
    class Meta:
        model = User
        fields = ("email", "full_name", "position", "password1", "password2")
    
    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            validate_corporate_email(email)
        return email
    
    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name")
        if full_name:
            validate_full_name(full_name)
        return full_name
