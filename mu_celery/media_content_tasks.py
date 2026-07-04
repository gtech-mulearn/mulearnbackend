"""
Celery tasks for the media_content module.

Keeping long-running or external-API-heavy work out of the request path.
"""
import logging

from celery import shared_task

from api.dashboard.media_content.image_utils import fetch_image_from_url

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def fetch_and_attach_poster(self, record_id: str, url: str, subdir: str, field: str = 'poster_thumbnail') -> None:
    """
    Download a remote poster image and write the result back to a MediaContent record.

    Args:
        record_id: PK of the MediaContent row to update.
        url:       The remote image URL to fetch.
        subdir:    Storage subdirectory under MEDIA_ROOT/media_content/ (e.g. 'posters').
        field:     Model field to update (default: 'poster_thumbnail').
    """
    # Import here to avoid circular imports at module load time.
    from db.events import MediaContent

    rel, err = fetch_image_from_url(url, subdir)
    if err:
        logger.warning(
            'fetch_and_attach_poster: could not download image for record %s '
            '(field=%s): %s',
            record_id, field, err,
        )
        try:
            raise self.retry(exc=RuntimeError(err))
        except self.MaxRetriesExceededError:
            logger.error(
                'fetch_and_attach_poster: gave up after %d retries for record %s (field=%s)',
                self.max_retries, record_id, field,
            )
        return

    updated = MediaContent.objects.filter(id=record_id).update(**{field: rel})
    if not updated:
        logger.warning(
            'fetch_and_attach_poster: MediaContent %s not found when trying to set %s',
            record_id, field,
        )
        return

    logger.info(
        'fetch_and_attach_poster: set %s=%s on MediaContent %s',
        field, rel, record_id,
    )
