"""Spec A §3.1 holds only if user emails are written through User.save()."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[3]  # mulearnbackend/
PATTERN = re.compile(r"\.update\([^)]*\bemail\s*=")
SCANNED = ("api", "db", "utils", "mu_celery")
EXCLUDED_PARTS = {"launchpad", "tests"}  # launchpad is deprecated and has its own users


def test_no_queryset_update_writes_an_email():
    offenders = []
    for top in SCANNED:
        for path in (ROOT / top).rglob("*.py"):
            if EXCLUDED_PARTS & set(path.parts):
                continue
            if PATTERN.search(path.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], f"QuerySet.update(email=…) bypasses User.save(): {offenders}"
