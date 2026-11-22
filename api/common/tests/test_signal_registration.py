"""The cache and landing-stats receivers are registered by ApiConfig.ready(), once (issue 0030).

They used to be registered only because the WebSocket routing imported api/common/common_consumer.py,
so they never ran in Celery workers.
"""

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.db.models.signals import post_delete, post_save

ROOT = Path(__file__).resolve().parents[3]
SIGNALS = ROOT / "api" / "common" / "signals.py"

# receiver name -> the models it listens to, on both post_save and post_delete
EXPECTED = {
    "db_signals": ["db.User", "db.LearningCircle", "db.InterestGroup", "db.UserRoleLink", "db.Organization"],
    "handle_org_link_cache": ["db.UserOrganizationLink"],
    "handle_ig_link_cache": ["db.UserIgLink"],
    "handle_session_cache": ["db.MentorshipSession"],
    "handle_karma_cache": ["db.KarmaActivityLog"],
}

# Runs in a fresh process: boot Django, never import a routing module, then report how many times
# each receiver is connected for each signal and model.
PROBE = """
import json, sys
import django
django.setup()
from django.apps import apps
from django.db.models.signals import post_delete, post_save
expected = json.loads(sys.argv[1])

def live(signal, sender):
    found = signal._live_receivers(sender)
    return [*found[0], *found[1]] if isinstance(found, tuple) else list(found)

counts = {}
for name, labels in expected.items():
    for label in labels:
        model = apps.get_model(label)
        for signal_name, signal in (("post_save", post_save), ("post_delete", post_delete)):
            matches = [r for r in live(signal, model) if getattr(r, "__name__", "") == name]
            counts[f"{name} {signal_name} {label}"] = len(matches)
routing = sorted(m for m in sys.modules if m in ("api.routing", "api.common.routing", "api.common.common_consumer"))
print(json.dumps({"counts": counts, "routing": routing}))
"""


def live_receivers(signal, sender):
    found = signal._live_receivers(sender)
    return [*found[0], *found[1]] if isinstance(found, tuple) else list(found)


def connections(name, signal, label):
    from django.apps import apps

    return [r for r in live_receivers(signal, apps.get_model(label)) if getattr(r, "__name__", "") == name]


def test_the_receivers_are_registered_in_a_process_that_never_imports_the_routing():
    env = {
        **os.environ,
        "DATABASE_ENGINE": "django.db.backends.sqlite3",
        "DATABASE_NAME": ":memory:",
        "DJANGO_SETTINGS_MODULE": "mulearnbackend.settings",
    }
    result = subprocess.run(
        [sys.executable, "-c", PROBE, json.dumps(EXPECTED)], cwd=ROOT, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout.strip().splitlines()[-1])

    assert report["routing"] == []
    assert report["counts"] == {key: 1 for key in report["counts"]}
    assert len(report["counts"]) == 2 * sum(len(labels) for labels in EXPECTED.values())


@pytest.mark.parametrize("signal", [post_save, post_delete], ids=["post_save", "post_delete"])
@pytest.mark.parametrize(("name", "label"), [(name, label) for name, labels in EXPECTED.items() for label in labels])
def test_each_receiver_is_connected_exactly_once_even_after_the_routing_is_imported(name, label, signal):
    import api.common.routing  # noqa: F401  the ASGI process imports this

    assert post_save.has_listeners(__import__("django.apps").apps.apps.get_model(label))
    assert len(connections(name, signal, label)) == 1


def test_the_signals_module_doesnt_import_channels_at_module_level():
    tree = ast.parse(SIGNALS.read_text(encoding="utf-8"))
    top_level = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_level.add(node.module)

    assert not {module for module in top_level if module.split(".")[0] in ("channels", "asgiref")}


def test_the_consumer_module_has_no_receivers_left():
    from api.common import common_consumer

    assert not [name for name in EXPECTED if hasattr(common_consumer, name)]
