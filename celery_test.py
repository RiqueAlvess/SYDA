#!/usr/bin/env python
import os
import django
import time
from datetime import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "data_saas.settings")
django.setup()

from data_saas.celery import app
from employees.tasks import sync_employees_task

print(f"Running test task at {datetime.now().strftime('%H:%M:%S')}...")
result = sync_employees_task.delay(1, 1)
print(f"Task ID: {result.id}")
print("Waiting for result...")

for i in range(10):
    if result.ready():
        print(f"Task finished with result: {result.result}")
        break
    print(f"Still waiting... ({i+1}/10)")
    time.sleep(1)

if not result.ready():
    print("Task is still running in the background.")
    print("Check celery worker logs to see progress.")