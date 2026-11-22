"""A stand-in for legacy code that calls a command inside its own transaction (issue 0021).

It lives outside building_blocks/ and modules/, so @command sees it as the legacy call site
"tests/command_callers.py::legacy_caller".
"""

from django.db import transaction


def legacy_caller(command_function, *args):
    with transaction.atomic():
        return command_function(*args)
