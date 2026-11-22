# Probe for PR #3424: a Django removal warning raised in new code must fail the run. Reverted next.
import warnings

from django.utils.deprecation import RemovedInDjango51Warning


def test_probe_raises_a_removal_warning():
    warnings.warn("probe: going away", RemovedInDjango51Warning, stacklevel=1)
