from django.db import models

class Client(models.Model):
    """Modelo para cliente"""
    name = models.CharField(max_length=100)
    subdomain = models.CharField(max_length=100, unique=True)
    paid_until = models.DateField(null=True, blank=True)
    on_trial = models.BooleanField(default=True)
    created_on = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return self.name

# Base para modelos específicos de tenant
class ClientRelatedModel(models.Model):
    """Classe base abstrata para modelos relacionados a clientes"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    
    class Meta:
        abstract = True
