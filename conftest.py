"""Root pytest conftest.

The db.* models are all `managed = False` and the project ships no migrations,
so Django has to be set up explicitly before any test module imports a model.
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mulearnbackend.settings")
django.setup()
