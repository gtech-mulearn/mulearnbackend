"""Every Celery task is routed to a named queue, and every beat entry resolves (issue 0064, ADR-042)."""

import json
import os
import pkgutil
import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings

import mu_celery
from mulearnbackend.celery import app
from mulearnbackend.celery_routing import LEGACY_QUEUE, QUEUES, TASK_ROUTES, matching_routes, unrouted

ROOT = Path(__file__).resolve().parents[2]

# What a worker registers: a fresh process that imports only what the Celery app imports.
WORKER_TASKS = """
import json
import django
django.setup()
from mulearnbackend.celery import app
app.loader.import_default_modules()
print(json.dumps(sorted(name for name in app.tasks if not name.startswith("celery."))))
"""


@pytest.fixture(scope="module")
def worker_tasks():
    env = {**os.environ, "DATABASE_ENGINE": "django.db.backends.sqlite3", "DATABASE_NAME": ":memory:"}
    result = subprocess.run([sys.executable, "-c", WORKER_TASKS], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_every_mu_celery_module_is_imported_by_the_celery_app():
    modules = {f"mu_celery.{module.name}" for module in pkgutil.iter_modules(mu_celery.__path__)}

    assert modules <= set(app.conf.include)


def test_a_worker_registers_tasks(worker_tasks):
    assert "mu_celery.push_tasks.send_activity_push" in worker_tasks
    assert len(worker_tasks) > 20


def test_every_registered_task_has_exactly_one_route(worker_tasks):
    assert unrouted(worker_tasks) == []
    assert {name: matching_routes(name) for name in worker_tasks if len(matching_routes(name)) > 1} == {}


def test_a_task_without_a_route_is_reported():
    assert unrouted(["mu_celery.new_module.some_task", "mu_celery.push_tasks.anything"]) == [
        "mu_celery.new_module.some_task"
    ]


def test_every_beat_entry_names_a_task_a_worker_registers(worker_tasks):
    schedule = settings.CELERY_BEAT_SCHEDULE
    missing = {key: entry["task"] for key, entry in schedule.items() if entry["task"] not in worker_tasks}

    assert missing == {}


def test_every_route_names_a_declared_queue():
    assert {route["queue"] for route in TASK_ROUTES.values()} <= set(QUEUES)


def test_the_celery_app_declares_the_queues_and_uses_the_routes():
    declared = {queue.name for queue in app.conf.task_queues}

    assert declared == {*QUEUES, LEGACY_QUEUE}
    assert app.conf.task_default_queue == "default"
    assert app.conf.task_routes == TASK_ROUTES


@pytest.mark.parametrize(
    ("task", "queue"),
    [
        ("mu_celery.push_tasks.send_activity_push", "notifications"),
        ("mu_celery.task.send_email", "notifications"),
        ("mu_celery.leaderboard_cron.refresh_leaderboards", "projections"),
        ("mu_celery.org_aggregates_cron.refresh_org_aggregates", "projections"),
        ("mu_celery.media_content_tasks.fetch_and_attach_poster", "bulk"),
        ("mu_celery.alumni_cron.update_alumni_status_cron", "default"),
    ],
)
def test_celery_sends_each_task_to_its_queue(task, queue):
    assert app.amqp.router.route({}, task)["queue"].name == queue


def test_local_workers_consume_every_queue():
    compose = (ROOT / "docker-compose.local.yml").read_text(encoding="utf-8")
    worker = re.search(r"celery -A mulearnbackend\.celery worker[^\n]*", compose).group(0)
    queues = re.search(r"-Q (\S+)", worker).group(1).split(",")

    assert sorted(queues) == sorted(QUEUES)
