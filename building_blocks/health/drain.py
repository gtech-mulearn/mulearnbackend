"""The drain flag: while its file exists, readiness fails, so the load balancer stops sending
new requests to this node before a deploy stops it. `touch` the file to drain; delete it to
take traffic again."""

import os

from django.conf import settings

DEFAULT_DRAIN_FLAG_PATH = "/tmp/mulearn-drain"


def is_draining() -> bool:
    return os.path.exists(getattr(settings, "DRAIN_FLAG_PATH", DEFAULT_DRAIN_FLAG_PATH))
