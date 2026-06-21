import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mulearnbackend.settings')
django.setup()

from db.task import TaskType

print("Task Types:")
for tt in TaskType.objects.all():
    print(tt.title)
