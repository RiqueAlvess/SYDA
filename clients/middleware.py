from django.utils.deprecation import MiddlewareMixin

class ClientMiddleware(MiddlewareMixin):
    """Middleware para adicionar o cliente atual à requisição"""
    
    def process_request(self, request):
        if request.user.is_authenticated:
            request.client = request.user.client
        else:
            request.client = None
        return None
