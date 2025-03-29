from django.utils.deprecation import MiddlewareMixin
from django.db.utils import ProgrammingError

class ClientMiddleware(MiddlewareMixin):
    """Middleware para adicionar o cliente atual à requisição"""
    
    def process_request(self, request):
        if request.user.is_authenticated:
            try:
                # Tenta acessar o cliente, mas captura erro se a coluna não existir
                request.client = request.user.client
            except ProgrammingError as e:
                # Verifica se o erro é sobre a coluna client_id
                if 'client_id' in str(e):
                    request.client = None
                    print("ATENÇÃO: Coluna client_id não existe na tabela accounts_user.")
                    # Tenta criar a coluna automaticamente
                    try:
                        from django.db import connection
                        with connection.cursor() as cursor:
                            cursor.execute("""
                            ALTER TABLE accounts_user 
                            ADD COLUMN client_id INTEGER REFERENCES clients_client(id) 
                            ON DELETE CASCADE;
                            """)
                            print("Coluna client_id adicionada com sucesso!")
                    except Exception as fix_error:
                        print(f"Erro ao adicionar coluna: {fix_error}")
                else:
                    # Se for outro erro, propaga
                    raise
        else:
            request.client = None
        return None
