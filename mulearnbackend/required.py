"""Collect missing required settings into one clear error.

A stop-gap until typed configuration (issue 0020): settings.py calls
``required(name)`` for values that have no default. Each missing name is
recorded here; settings.py raises once at the end with the full list instead
of failing on the first one during import.
"""
from decouple import config as decouple_config

MISSING: set[str] = set()


def required(name: str, **kwargs):
    """Read a setting that must be present, recording it if it is absent.

    Extra keyword arguments such as ``cast`` are passed through to decouple,
    so a required setting keeps exactly the conversion it had before.
    """
    value = decouple_config(name, default=None, **kwargs)
    if value is None:
        MISSING.add(name)
    return value
