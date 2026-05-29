"""Model registry for the ``db`` app.

This app keeps its models split across sibling modules (``db/task.py``,
``db/company.py``, …) instead of a single file. Django automatically imports
``<app>.models`` during ``apps.populate()`` (the canonical model-registration
phase, before ``AppConfig.ready()``), so importing every model module here is
what registers all models and lets lazy string FK references such as
``'db.Company'`` / ``'db.InterestGroup'`` resolve.

When you add a new model module under ``db/``, add it to the import list below.
"""

# noqa: F401 — imported for the side effect of registering models.
from db import (  # noqa: F401
    achievement,
    campus,
    company,
    donation,
    donor,
    events,
    hackathon,
    integrations,
    launchpad,
    learning_circle,
    mentor,
    mentor_task_request,
    notification,
    organization,
    projects,
    settings,
    skill,
    task,
    url_shortener,
    user,
)
