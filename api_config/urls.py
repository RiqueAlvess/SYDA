from django.urls import path
from . import views

urlpatterns = [
    path('config/', views.ApiConfigView.as_view(), name='api_config'),
    path('sync-logs/', views.SyncLogListView.as_view(), name='sync_logs'),
]