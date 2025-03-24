from django.contrib import admin
from .models import EmployeeCredentials, AbsenceCredentials, SyncLog

@admin.register(EmployeeCredentials)
class EmployeeCredentialsAdmin(admin.ModelAdmin):
    list_display = ('company', 'user', 'is_active', 'is_inactive', 'is_away', 'is_pending', 'is_vacation', 'updated_at')
    list_filter = ('is_active', 'is_inactive', 'is_away', 'is_pending', 'is_vacation', 'client')
    search_fields = ('company', 'user__email', 'code')
    date_hierarchy = 'updated_at'

@admin.register(AbsenceCredentials)
class AbsenceCredentialsAdmin(admin.ModelAdmin):
    list_display = ('main_company', 'work_company', 'user', 'start_date', 'end_date', 'updated_at')
    list_filter = ('client', 'start_date', 'end_date')
    search_fields = ('main_company', 'work_company', 'user__email', 'code')
    date_hierarchy = 'updated_at'

@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ('api_type', 'company', 'user', 'status', 'records_processed', 'records_success', 'records_error', 'start_time')
    list_filter = ('api_type', 'status', 'client')
    search_fields = ('company', 'user__email', 'error_message')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'start_time', 'end_time')