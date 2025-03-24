# cleanup.py
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "data_saas.settings")
django.setup()

from api_config.models import SyncLog
from django.utils import timezone

# Marcar todas sincronizações pendentes como erro
stuck_logs = SyncLog.objects.filter(end_time__isnull=True)
count = stuck_logs.count()

for log in stuck_logs:
    log.status = 'error'
    log.end_time = timezone.now()
    log.error_message = "Sincronização interrompida manualmente."
    log.save()

print(f"✅ Limpeza concluída. {count} sincronizações travadas foram resolvidas.")