#!/bin/bash
# init.sh - Script de inicialização para o deploy no Render

echo "----------------------------------------------"
echo "Iniciando script de inicialização..."
echo "----------------------------------------------"

# Verificar se estamos em ambiente de deploy
if [ -z "$RENDER" ]; then
  echo "Não estamos no ambiente Render, executando em modo local"
fi

echo "Executando migrations..."
# Executar todas as migrações - isso aplicará a migração nova que adiciona client_id
python manage.py migrate

# Criar cliente padrão se não existir
echo "Criando cliente padrão se necessário..."
python manage.py create_default_client

# Coletar arquivos estáticos
echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# Corrigir permissões de clientes para usuários existentes se necessário
echo "Verificando usuários sem cliente..."
python - << EOF
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "data_saas.settings")
django.setup()

from django.contrib.auth import get_user_model
from clients.models import Client

User = get_user_model()
default_client = Client.objects.first()

if default_client:
    users_without_client = User.objects.filter(client__isnull=True)
    count = users_without_client.count()
    
    if count > 0:
        print(f"Encontrados {count} usuários sem cliente. Associando ao cliente padrão: {default_client.name}")
        users_without_client.update(client=default_client)
        print("Usuários atualizados com sucesso!")
    else:
        print("Todos os usuários já possuem cliente associado.")
else:
    print("Nenhum cliente encontrado. Execute create_default_client primeiro.")
EOF

echo "----------------------------------------------"
echo "Inicialização concluída!"
echo "----------------------------------------------"
