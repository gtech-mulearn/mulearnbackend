"""Choose which beat schedules a deployment registers (the BEAT_SCHEDULES setting).

A stopgap until schedules are enabled one at a time behind flags (ADR-042). This is
deployment configuration, not a feature switch.
"""
from django.core.exceptions import ImproperlyConfigured

KEYWORDS = ("all", "none")


def select_schedules(schedule: dict, selection: str) -> dict:
    """Return a new dict with the entries of ``schedule`` that ``selection`` chooses.

    ``selection`` is ``all`` (also when unset or empty), ``none``, or a comma-separated
    list of schedule names. Keywords are case-insensitive and valid only on their own.
    Spaces, empty items and repeats are ignored. Unknown names raise ImproperlyConfigured.
    """
    text = (selection or "").strip()
    if not text or text.lower() == "all":
        return dict(schedule)
    if text.lower() == "none":
        return {}
    names = list(dict.fromkeys(n.strip() for n in text.split(",") if n.strip()))
    keywords = [n for n in names if n.lower() in KEYWORDS]
    if keywords:
        raise ImproperlyConfigured(
            f"BEAT_SCHEDULES: {', '.join(keywords)} must be used on its own, not with other names."
        )
    unknown = [n for n in names if n not in schedule]
    if unknown:
        raise ImproperlyConfigured(
            f"BEAT_SCHEDULES names unknown schedules: {', '.join(unknown)}. "
            f"Known schedules: {', '.join(sorted(schedule))}."
        )
    return {n: schedule[n] for n in names}
