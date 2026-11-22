"""/healthz/live and /healthz/ready: plain Django views, outside /api/v1/, with no authentication.

Django logs only failed requests, so successful health checks write no log lines.
"""

from django.core.cache import caches
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_safe

from building_blocks.health import drain


def dependencies_answer() -> bool:
    """True if this process's database connection and cache both answer."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        caches["default"].get("healthz")
    except Exception:
        return False
    return True


@require_safe
def live(request):
    """200 while the process is up, even while draining."""
    return JsonResponse({"status": "ok"})


@require_safe
def ready(request):
    """200 when this process can serve; 503 while draining or when its database or cache fails."""
    if drain.is_draining():
        return JsonResponse({"status": "draining"}, status=503)
    if not dependencies_answer():
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ready"})
