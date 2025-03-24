from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Cria perfil de usuário quando um novo usuário é criado."""
    # Aqui você pode adicionar lógica para criar perfis de usuário
    # ou configurações específicas após a criação de um novo usuário
    if created:
        pass
