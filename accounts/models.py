from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    """Gerenciador de modelo para usuário customizado."""
    
    def create_user(self, email, full_name, position, password=None, **extra_fields):
        """Cria e salva um usuário com o email, nome completo e senha fornecidos."""
        if not email:
            raise ValueError(_("O email é obrigatório"))
        if not full_name:
            raise ValueError(_("O nome completo é obrigatório"))
        if not position:
            raise ValueError(_("O cargo é obrigatório"))
            
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            full_name=full_name,
            position=position,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, full_name, position, password=None, **extra_fields):
        """Cria e salva um superusuário com o email, nome completo e senha fornecidos."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        
        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser deve ter is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser deve ter is_superuser=True."))
            
        return self.create_user(email, full_name, position, password, **extra_fields)

class User(AbstractUser):
    """Modelo de usuário personalizado."""
    username = None
    email = models.EmailField(_("endereço de email"), unique=True)
    full_name = models.CharField(_("nome completo"), max_length=150)
    position = models.CharField(_("cargo"), max_length=100)
    # Adicionar relacionamento com cliente
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, 
                              null=True, blank=True, 
                              verbose_name=_("Cliente"),
                              related_name="users")
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "position"]
    
    objects = UserManager()
    
    def __str__(self):
        return self.email
