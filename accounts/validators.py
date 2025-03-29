import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class SpecialCharacterValidator:
    """Validador que exige pelo menos um caractere especial."""
    
    def validate(self, password, user=None):
        """O parâmetro 'user' é necessário para compatibilidade com a interface de validação do Django."""
        if not re.findall(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise ValidationError(
                _("A senha deve conter pelo menos um caractere especial."),
                code="password_no_special_character",
            )
    
    def get_help_text(self):
        return _("Sua senha deve conter pelo menos um caractere especial.")


def validate_corporate_email(email):
    """Valida se o email é corporativo (não é de provedores comuns)."""
    common_domains = [
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", 
        "live.com", "msn.com", "icloud.com", "aol.com", 
        "protonmail.com", "mail.com"
    ]
    domain = email.split("@")[-1].lower()
    
    if domain in common_domains:
        raise ValidationError(
            _("Por favor, use um email corporativo. Emails pessoais como Gmail, Hotmail, etc. não são permitidos."),
            code="invalid_email_domain"
        )


def validate_full_name(name):
    """Valida se o nome tem pelo menos duas palavras."""
    words = name.split()
    if len(words) < 2:
        raise ValidationError(
            _("Por favor, forneça seu nome completo (nome e sobrenome)."),
            code="invalid_full_name"
        )
