"""Collect missing required settings, so startup fails once with every missing name.

A stop-gap until typed configuration (docs/architecture, issue 0020). It imports
nothing from the project, so it can be tested without Django set up.
"""
from django.core.exceptions import ImproperlyConfigured


def make_required(read, missing: list):
    """Return ``required(name, cast=None)``: the value from ``read``, or None after noting ``name`` in ``missing``.

    ``read`` is decouple's ``config``; it is called with ``default=None`` so an
    absent value doesn't raise. ``cast`` is applied only to a present value.
    """

    def required(name: str, cast=None):
        value = read(name, default=None)
        if value is None:
            missing.append(name)
            return None
        return cast(value) if cast else value

    return required


def raise_if_missing(missing: list) -> None:
    """Raise one ImproperlyConfigured listing every missing name, sorted."""
    if missing:
        raise ImproperlyConfigured(
            "Missing required settings: " + ", ".join(sorted(set(missing)))
            + ". Set them in the environment or in .env (see .env.sample)."
        )
