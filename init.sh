#!/bin/bash
# init.sh - Script de inicialização para o deploy no Render

echo "Iniciando script de inicialização..."

# Executar migrações
echo "Aplicando migrações do Django..."
python manage.py migrate

# Criar cliente padrão se não existir
echo "Criando cliente padrão se necessário..."
python manage.py create_default_client

# Coletar arquivos estáticos
echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "Inicialização concluída!"
