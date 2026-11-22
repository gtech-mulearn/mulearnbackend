"""Django removal warnings are errors in new code and counted in legacy code (issue 0041, ADR-051).

The root conftest adds one pytest filter per removal warning that the installed Django defines.
The list is read from Django rather than written out: RemovedInDjango60Warning only exists from
Django 5.1, and RemovedInDjango50Warning is gone in 5.0, so a fixed list would stop pytest from
starting either before or after an upgrade.
"""

import re

import django.utils.deprecation

# The packages that hold new code. A warning attributed to a module in one of them is an error.
NEW_CODE = r"(building_blocks|modules|tests)(\.|$)"
_REMOVAL = re.compile(r"RemovedInDjango\d+Warning")


def removal_warnings() -> list[type[Warning]]:
    """Every RemovedInDjangoNNWarning class the installed Django defines."""
    names = sorted(name for name in dir(django.utils.deprecation) if _REMOVAL.fullmatch(name))
    return [getattr(django.utils.deprecation, name) for name in names]


def error_filters() -> list[str]:
    """pytest filterwarnings lines that turn each removal warning into an error in new code."""
    return [f"error::{category.__module__}.{category.__name__}:{NEW_CODE}" for category in removal_warnings()]


def count_removal_warnings(reports) -> int:
    """How many of pytest's recorded warnings are Django removal warnings."""
    return sum(1 for report in reports if _REMOVAL.search(report.message))
