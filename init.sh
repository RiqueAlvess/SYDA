#!/bin/bash
# init.sh - Script de inicialização para o deploy no Render

echo "----------------------------------------------"
echo "Iniciando script de inicialização..."
echo "----------------------------------------------"

# Verificar e corrigir o banco de dados
echo "Verificando banco de dados..."
python - << EOF
import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "data_saas.settings")
django.setup()

from django.db import connection

try:
    with connection.cursor() as cursor:
        # Verificar se a coluna client_id existe
        cursor.execute("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = 'accounts_user' 
            AND column_name = 'client_id'
        );
        """)
        column_exists = cursor.fetchone()[0]
        
        if not column_exists:
            print("A coluna client_id não existe. Adicionando...")
            cursor.execute("""
            ALTER TABLE accounts_user 
            ADD COLUMN client_id INTEGER REFERENCES clients_client(id) 
            ON DELETE CASCADE;
            """)
            print("Coluna client_id adicionada com sucesso!")
        else:
            print("A coluna client_id já existe.")
except Exception as e:
    print(f"Erro ao verificar/adicionar coluna: {e}")
EOF

# Executar migrações
echo "Aplicando migrações do Django..."
python manage.py migrate

# Criar cliente padrão se não existir
echo "Criando cliente padrão se necessário..."
python manage.py create_default_client

# Coletar arquivos estáticos
echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "----------------------------------------------"
echo "Inicialização concluída!"
echo "----------------------------------------------"
