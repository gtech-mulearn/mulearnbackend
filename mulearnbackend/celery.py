import os
import pkgutil

from celery import Celery
from kombu import Queue

import mu_celery
from mulearnbackend.celery_routing import LEGACY_QUEUE, QUEUES, TASK_ROUTES

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mulearnbackend.settings")

# Every module in mu_celery, so every task (and every beat entry's task) is registered in the
# worker. A hand-written list left 7 of the 14 beat entries pointing at tasks no worker had
# (issue 0064); autodiscover_tasks() below only finds tasks.py in installed apps.
TASK_MODULES = sorted(f"mu_celery.{module.name}" for module in pkgutil.iter_modules(mu_celery.__path__))

app = Celery("mulearnbackend", include=TASK_MODULES)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Named queues and routes (mulearnbackend/celery_routing.py). A worker started without -Q
# consumes every queue declared here.
app.conf.task_queues = [Queue(name) for name in (*QUEUES, LEGACY_QUEUE)]
app.conf.task_default_queue = "default"
app.conf.task_routes = TASK_ROUTES

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
