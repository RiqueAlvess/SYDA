from django.core.management.base import BaseCommand
from clients.models import Client

class Command(BaseCommand):
    help = 'Cria um cliente padrão para o sistema se não existir nenhum'

    def handle(self, *args, **kwargs):
        if Client.objects.count() == 0:
            client = Client.objects.create(
                name='Cliente Padrão',
                subdomain='default'
            )
            self.stdout.write(self.style.SUCCESS(f'Cliente padrão criado com ID {client.id}'))
        else:
            self.stdout.write(self.style.WARNING('Já existe pelo menos um cliente no sistema'))