from django.urls import path
from . import views

urlpatterns = [
    path('', views.EmployeeListView.as_view(), name='employee_list'),
    path('<int:pk>/', views.EmployeeDetailView.as_view(), name='employee_detail'),
    path('sync/', views.sync_employees, name='sync_employees'),
    path('sync-absences/', views.sync_absences, name='sync_absences'),
    path('sync-status/<int:sync_id>/', views.sync_status, name='sync_status'),
    path('sync-details/<int:sync_id>/', views.sync_details, name='sync_details'),
    path('sync-delete/<int:sync_id>/', views.sync_delete, name='sync_delete'),
    path('sync-stop/<int:sync_id>/', views.sync_stop, name='sync_stop'),
    
    # Adicione essas URLs para as APIs do dashboard
    path('api/dashboard/employees/', views.dashboard_employees_api, name='api_dashboard_employees'),
    path('api/dashboard/absences/', views.dashboard_absences_api, name='api_dashboard_absences'),
]