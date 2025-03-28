from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Cria perfil de usuário quando um novo usuário é criado.
    """
    if created:
        # Por enquanto, nenhuma ação adicional é necessária:
        pass  # Intencionalmente vazio, nada a executar no momento.
