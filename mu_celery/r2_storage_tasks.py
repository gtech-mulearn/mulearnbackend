"""
Celery tasks for utils/r2_storage.py.

POST /api/v1/media/upload/ writes to R2 immediately and hands back a key;
a record only points at that key later, in a separate call (see
utils/r2_storage.py and api/dashboard/ig/dash_ig_view.py). An upload that's
never attached — an abandoned form, an image replaced before saving — has
nothing referencing it and would otherwise sit in the bucket forever.
"""
import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task
from django.conf import settings

from db.task import InterestGroup
from utils import r2_storage

logger = logging.getLogger(__name__)

# Anything younger than this is left alone even if nothing references it yet,
# so an upload that's mid-flight (uploaded, not attached yet) is never caught
# by a race with the sweep.
ORPHAN_GRACE_PERIOD = timedelta(hours=24)

# One entry per MODULE_RULES key: how to look up the keys that module's own
# records currently point at. A module missing here is skipped with a
# warning rather than silently deleting objects nothing has vouched for.
_MODULE_REFERENCED_KEYS = {
    "ig_cover": lambda: set(
        InterestGroup.objects.exclude(cover_image_key__in=(None, ""))
        .values_list("cover_image_key", flat=True)
    ),
    "ig_icon": lambda: set(
        InterestGroup.objects.exclude(icon_image_key__in=(None, ""))
        .values_list("icon_image_key", flat=True)
    ),
}


@shared_task
def delete_orphaned_r2_uploads():
    """
    Deletes R2 objects older than ORPHAN_GRACE_PERIOD that no record
    references. Safe to run repeatedly: an object is only ever a candidate
    once it's both unreferenced and past the grace period, and re-running
    just finds nothing left to delete.
    """
    cutoff = datetime.now(timezone.utc) - ORPHAN_GRACE_PERIOD
    client = r2_storage.get_r2_client()
    paginator = client.get_paginator("list_objects_v2")
    deleted_counts = {}

    for module, rules in r2_storage.MODULE_RULES.items():
        referenced_lookup = _MODULE_REFERENCED_KEYS.get(module)
        if referenced_lookup is None:
            logger.warning(
                "delete_orphaned_r2_uploads: no referenced-key lookup for "
                "module %s, skipping",
                module,
            )
            continue

        referenced = referenced_lookup()
        deleted = 0

        for page in paginator.paginate(
            Bucket=settings.R2_BUCKET_NAME, Prefix=f"{rules['folder']}/"
        ):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key in referenced or obj["LastModified"] > cutoff:
                    continue
                client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
                deleted += 1

        if deleted:
            logger.info(
                "delete_orphaned_r2_uploads: removed %d orphaned object(s) "
                "for module %s",
                deleted, module,
            )
        deleted_counts[module] = deleted

    return deleted_counts
