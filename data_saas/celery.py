import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_saas.settings')

# Create the app instance
app = Celery('data_saas')

# Use a string here to avoid namespace issues
app.config_from_object('django.conf:settings', namespace='CELERY')

# Discover tasks automatically from all registered Django apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')