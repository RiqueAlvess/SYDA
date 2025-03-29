class ClientQuerySetMixin:
    """
    Mixin para filtrar querysets pelo cliente do usuário atual
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(self.request, 'client') and self.request.client:
            return queryset.filter(client=self.request.client)
        return queryset.none()  # Retorna queryset vazio se não houver cliente
