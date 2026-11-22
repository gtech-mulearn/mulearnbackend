import warnings
from types import SimpleNamespace

import pytest
from django.utils.deprecation import RemovedInDjango51Warning

from tests.deprecations import count_removal_warnings, removal_warnings


def emit(module, category=RemovedInDjango51Warning):
    """Raise a warning attributed to ``module``; return the warnings recorded instead of raised."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.warn_explicit("going away", category, "x.py", 1, module=module, registry={})
    return [item.category for item in caught]


def test_every_django_removal_warning_is_covered():
    assert RemovedInDjango51Warning in removal_warnings()
    assert all(category.__name__.startswith("RemovedInDjango") for category in removal_warnings())


@pytest.mark.parametrize("category", removal_warnings())
def test_a_removal_warning_raised_in_new_code_is_an_error(category):
    with pytest.raises(category):
        # stacklevel=1 attributes the warning to this module, under building_blocks/tests/.
        warnings.warn("going away", category, stacklevel=1)


@pytest.mark.parametrize("module", ["building_blocks", "building_blocks.clock", "modules.events.services", "tests.x"])
def test_every_new_code_package_is_covered(module):
    with pytest.raises(RemovedInDjango51Warning):
        emit(module)


@pytest.mark.parametrize(
    "module",
    [
        "api.dashboard.views",
        "utils.response",
        "db.user",
        "mu_celery.tasks",
        "django.conf",
        "building_blocksx",
        "testsuite",
    ],
)
def test_a_removal_warning_from_legacy_code_stays_a_warning(module):
    assert emit(module) == [RemovedInDjango51Warning]


def test_other_deprecation_warnings_in_new_code_stay_warnings():
    assert emit("building_blocks.clock", DeprecationWarning) == [DeprecationWarning]


def test_the_summary_counts_django_removal_warnings_only():
    reports = [
        SimpleNamespace(message="api/x.py:3: RemovedInDjango51Warning: The X setting is deprecated."),
        SimpleNamespace(message="api/y.py:9: RemovedInDjango50Warning: Y is going away."),
        SimpleNamespace(message="utils/z.py:1: DeprecationWarning: something else"),
    ]

    assert count_removal_warnings(reports) == 2
    assert count_removal_warnings([]) == 0
