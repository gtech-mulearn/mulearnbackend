import csv
import datetime
import logging
import time
import re
import gzip
import io
import os
import uuid
from datetime import timedelta

import openpyxl
import pytz
import requests
from decouple import config
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.db.models.query import QuerySet
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from django.template.loader import render_to_string
import string, random
from django.utils.timezone import now
from PIL import Image

# Upper bound for the client-supplied `perPage` query parameter. Applies to
# every paginated endpoint; callers that genuinely need the full set pass
# is_pagination=False and are unaffected.
MAX_PAGE_SIZE = 1000


def check_alumni_status(graduation_year):
    """
    Returns True if graduation_year is a valid 4-digit year and is in the past.
    Mirrors the logic from mu_celery/alumni_cron.py so is_alumni is always
    accurate at the point of creation or update — no cron lag.
    """
    if graduation_year and re.match(r'^[0-9]{4}$', str(graduation_year)):
        return int(graduation_year) < now().year
    return False


class CommonUtils:
    @staticmethod
    def get_paginated_queryset(
        queryset: QuerySet,
        request,
        search_fields,
        sort_fields: dict = None,
        is_pagination: bool = True,
        extra_q: Q = None,
    ) -> QuerySet:
        """
        Returns a paginated queryset based on the provided parameters.

        Args:
            - queryset (QuerySet): The original queryset to be paginated.
            - request: The request object containing query parameters.
            - search_fields (list): The list of fields to search for.
            - sort_fields (dict, optional): A dictionary mapping sort fields. Defaults to None.
            - is_pagination (bool, optional): Flag indicating whether pagination should be applied. Defaults to True.
            - extra_q (Q, optional): An additional condition OR'd into the search filter, for
              matching values that aren't backed by a real searchable column (e.g. a display-only
              label). Ignored unless a search query is present.

        Returns:
            - QuerySet or dict: The paginated queryset or a dictionary containing the paginated queryset and pagination information.
        """
        if sort_fields is None:
            sort_fields = {}

        if not isinstance(queryset, QuerySet):
            # A few views build their rows in Python (or serve them from a
            # cache) and pass a list. Search and sort are then applied in Python
            # with the same meaning; pagination output is identical.
            return CommonUtils._paginate_list(
                list(queryset), request, search_fields, sort_fields, is_pagination
            )

        try:
            page = int(request.query_params.get("pageIndex", 1))
        except ValueError:
            page = 1
            
        try:
            per_page = int(request.query_params.get("perPage", 10))
        except ValueError:
            per_page = 10

        # Without a ceiling, ?perPage=999999 turns any paginated endpoint into a
        # single-request denial of service. The largest value the frontend sends
        # is 1000; bulk exports bypass pagination entirely via is_pagination=False.
        per_page = max(1, min(per_page, MAX_PAGE_SIZE))
        search_query = request.query_params.get("search")
        sort_by = request.query_params.get("sortBy")

        if search_query:
            query = Q()
            for field in search_fields:
                query |= Q(**{f"{field}__icontains": search_query})
            if extra_q:
                query |= extra_q

            queryset = queryset.filter(query)

        # "pk" tiebreak: the requested field alone is rarely unique (e.g. many
        # rows share a start_datetime or a status), so without it, rows tied
        # on sort_field_name can be returned in a different relative order
        # between requests, causing offset-paginated clients to skip or see
        # duplicate rows across pages. Skipped for .values()/.values_list()
        # querysets (queryset._fields is not None): ordering by a field not
        # already in the values()/annotate() selection folds that field into
        # GROUP BY, silently corrupting any aggregate() computed there.
        is_grouped = queryset._fields is not None
        if sort_by:
            is_descending = sort_by.startswith("-")
            sort = sort_by[1:] if is_descending else sort_by
            if sort_mapped := sort_fields.get(sort):
                if isinstance(sort_mapped, (list, tuple)):
                    order_fields = [
                        f if f.startswith("-") else f"-{f}" if is_descending else f
                        for f in sort_mapped
                    ]
                else:
                    order_fields = [
                        sort_mapped if sort_mapped.startswith("-") else f"-{sort_mapped}" if is_descending else sort_mapped
                    ]

                if not is_grouped and "pk" not in order_fields and "-pk" not in order_fields:
                    order_fields.append("pk")

                queryset = queryset.order_by(*order_fields)
        elif is_pagination and not is_grouped and not queryset.ordered:
            # Paginator does LIMIT/OFFSET, which MySQL does not guarantee a
            # stable row order for across separate requests without an
            # explicit order_by — same failure mode as above, but for the
            # (more common) case where the caller passed no ?sortBy= at all
            # and the queryset has no ordering of its own to fall back on.
            queryset = queryset.order_by("pk")
        if is_pagination:
            paginator = Paginator(queryset, per_page)
            try:
                queryset = paginator.page(page)
            except PageNotAnInteger:
                queryset = paginator.page(1)
            except EmptyPage:
                queryset = paginator.page(paginator.num_pages)

            return {
                "queryset": queryset,
                "pagination": {
                    "count": paginator.count,
                    "totalPages": paginator.num_pages,
                    "isNext": queryset.has_next(),
                    "isPrev": queryset.has_previous(),
                    "nextPage": (
                        queryset.next_page_number() if queryset.has_next() else None
                    ),
                },
            }

        return queryset

    @staticmethod
    def _lookup(item, path):
        """Resolve "a__b" on a dict or an object, None when any step is missing."""
        value = item
        for part in path.split("__"):
            if value is None:
                return None
            value = value.get(part) if isinstance(value, dict) else getattr(value, part, None)
        return value

    @staticmethod
    def _paginate_list(items, request, search_fields, sort_fields, is_pagination):
        """List counterpart of get_paginated_queryset (same parameters and output)."""
        try:
            page = int(request.query_params.get("pageIndex", 1))
        except ValueError:
            page = 1
        try:
            per_page = int(request.query_params.get("perPage", 10))
        except ValueError:
            per_page = 10
        per_page = max(1, min(per_page, MAX_PAGE_SIZE))

        if search_query := request.query_params.get("search"):
            needle = search_query.casefold()
            items = [
                item
                for item in items
                if any(
                    (value := CommonUtils._lookup(item, field)) is not None
                    and needle in str(value).casefold()
                    for field in search_fields
                )
            ]

        if sort_by := request.query_params.get("sortBy"):
            descending = sort_by.startswith("-")
            sort_mapped = sort_fields.get(sort_by[1:] if descending else sort_by)
            if sort_mapped:
                fields = sort_mapped if isinstance(sort_mapped, (list, tuple)) else [sort_mapped]
                # Stable sorts applied last-field-first give a multi-key order;
                # None sorts first ascending, like MySQL.
                for field in reversed(fields):
                    field_desc = descending != field.startswith("-")
                    name = field.lstrip("-")
                    items.sort(
                        key=lambda item: (
                            (value := CommonUtils._lookup(item, name)) is not None,
                            value if value is not None else 0,
                        ),
                        reverse=field_desc,
                    )

        if not is_pagination:
            return items

        paginator = Paginator(items, per_page)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        return {
            "queryset": page_obj,
            "pagination": {
                "count": paginator.count,
                "totalPages": paginator.num_pages,
                "isNext": page_obj.has_next(),
                "isPrev": page_obj.has_previous(),
                "nextPage": page_obj.next_page_number() if page_obj.has_next() else None,
            },
        }

    @staticmethod
    def generate_csv(queryset: QuerySet, csv_name: str) -> HttpResponse:
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{csv_name}.csv"'

        if not queryset:
            fieldnames = []
        else:
            # Collect all unique keys across all rows
            fieldnames = []
            for row in queryset:
                for key in row.keys():
                    if key not in fieldnames:
                        fieldnames.append(key)

        writer = csv.DictWriter(response, fieldnames=fieldnames, extrasaction='ignore')
        if fieldnames:
            writer.writeheader()
            writer.writerows(queryset)

        compressed_response = HttpResponse(
            gzip.compress(response.content),
            content_type="text/csv",
        )
        compressed_response["Content-Disposition"] = (
            f'attachment; filename="{csv_name}.csv"'
        )
        compressed_response["Content-Encoding"] = "gzip"

        return compressed_response


def cache_view_response(key: str, timeout: int):
    """
    Cache a parameterless GET view's success envelope under one fixed key.

    Replacement for cache_page on endpoints whose response does not depend on
    the request. cache_page keys on the full URL including the query string,
    so every ?x=<random> stored another full copy (an unbounded key space in
    Redis). Only 200 responses are cached; the cached value is the rendered
    JSON, so the response bytes are identical to an uncached call. A cache
    outage falls back to running the view.
    """
    from functools import wraps
    from rest_framework.renderers import JSONRenderer
    from rest_framework.response import Response
    import json as _json
    from django.core.cache import cache as _cache

    def decorator(view_method):
        @wraps(view_method)
        def wrapper(view, request, *args, **kwargs):
            try:
                cached = _cache.get(key)
            except Exception:
                cached = None
            if cached is not None:
                return Response(data=cached, status=200)
            response = view_method(view, request, *args, **kwargs)
            if getattr(response, "status_code", None) == 200 and hasattr(response, "data"):
                try:
                    _cache.set(key, _json.loads(JSONRenderer().render(response.data)), timeout)
                except Exception:
                    pass
            return response

        return wrapper

    return decorator


class ImageUploadUtils:
    """
    Centralized image upload system: validate, store, resolve, and delete
    image files. Use this instead of duplicating size/type checks and
    FileSystemStorage boilerplate across views.

    Two storage modes are supported:
      - `save(filename, image)`: a caller-chosen fixed path that gets
        overwritten on every upload (e.g. a user's single profile cover).
      - `save_unique(directory, image)`: a generated UUID filename under a
        directory, using the extension detected from the actual image
        bytes (e.g. a gallery of project images).
    """

    MIN_SIZE_BYTES = 1 * 1024          # 1 KB
    MAX_SIZE_BYTES = 5 * 1024 * 1024   # 5 MB

    # Client-supplied content_type/filename extensions are spoofable, so the
    # canonical extension is always derived from Pillow's decoded format.
    ALLOWED_FORMATS = {
        "PNG": "png",
        "JPEG": "jpg",
        "GIF": "gif",
        "WEBP": "webp",
    }

    @classmethod
    def validate(cls, image, min_size: int = None, max_size: int = None) -> str | None:
        """
        Validates an uploaded image file's type, size bounds, and integrity.

        Args:
            image: An UploadedFile (e.g. request.FILES.get('image')).
            min_size: Minimum allowed size in bytes. Defaults to MIN_SIZE_BYTES.
            max_size: Maximum allowed size in bytes. Defaults to MAX_SIZE_BYTES.

        Returns:
            str | None: An error message if the image is invalid, else None.
        """
        min_size = cls.MIN_SIZE_BYTES if min_size is None else min_size
        max_size = cls.MAX_SIZE_BYTES if max_size is None else max_size

        if not image:
            return "No image file provided"

        if image.size < min_size:
            return f"Image must be at least {min_size // 1024} KB"

        if image.size > max_size:
            return f"Image must be under {max_size // (1024 * 1024)} MB"

        if cls._detect_format(image) is None:
            return f"Unsupported image format. Allowed: {', '.join(sorted(cls.ALLOWED_FORMATS.values()))}"

        return None

    @classmethod
    def _detect_format(cls, image) -> str | None:
        """
        Decodes the actual image bytes with Pillow and returns the
        canonical extension (e.g. "png"), or None if the file is corrupt,
        unreadable, or not one of ALLOWED_FORMATS. Leaves `image` seeked
        back to 0 so it remains usable for further reads (e.g. `.save()`).
        """
        image.seek(0)
        try:
            with Image.open(image) as img:
                img.verify()
        except Exception:
            image.seek(0)
            return None

        # verify() invalidates the Image object for further use, so the
        # format must be read from a freshly reopened handle.
        image.seek(0)
        try:
            with Image.open(image) as img:
                fmt = (img.format or "").upper()
        except Exception:
            image.seek(0)
            return None
        image.seek(0)

        return cls.ALLOWED_FORMATS.get(fmt)

    @staticmethod
    def _safe_relative_path(path: str) -> str:
        """
        Normalizes a storage-relative path and rejects any attempt to
        escape the storage root (e.g. "../../etc/passwd") or use an
        absolute path.
        """
        normalized = os.path.normpath(path).replace(os.sep, "/")
        if normalized.startswith("../") or normalized == ".." or normalized.startswith("/"):
            raise ValueError(f"Invalid storage path: {path!r}")
        return normalized

    @classmethod
    def save(cls, filename: str, image) -> str:
        """
        Saves an image to a fixed path, overwriting any existing file there.
        Callers are expected to have already run `validate()`.

        Args:
            filename: Storage-relative path, e.g. "user/cover/<user_id>.png".
            image: An UploadedFile (e.g. request.FILES.get('image')).

        Returns:
            str: The saved filename (same as the `filename` argument).
        """
        filename = cls._safe_relative_path(filename)
        fs = FileSystemStorage()
        # Must delete before save: FileSystemStorage.save() renames on
        # collision (e.g. "<name>_abc123.png") instead of overwriting, which
        # would desync any fixed path callers reconstruct from `filename`.
        if fs.exists(filename):
            fs.delete(filename)
        image.seek(0)
        fs.save(filename, image)
        return filename

    @classmethod
    def save_unique(cls, directory: str, image, min_size: int = None, max_size: int = None) -> tuple[str | None, str | None]:
        """
        Validates and saves an image under `directory/` with a generated
        UUID filename, using the extension detected from the actual image
        bytes. Use this for galleries/multi-image fields where each upload
        needs its own filename rather than a fixed overwritten path.

        Returns:
            tuple[str | None, str | None]: (relative_path, error_message) —
            exactly one of the two is None.
        """
        error = cls.validate(image, min_size=min_size, max_size=max_size)
        if error:
            return None, error

        ext = cls._detect_format(image)
        directory = cls._safe_relative_path(directory).strip("/")
        filename = f"{directory}/{uuid.uuid4()}.{ext}"

        fs = FileSystemStorage()
        image.seek(0)
        saved_name = fs.save(filename, image)
        return saved_name, None

    @classmethod
    def delete(cls, filename: str) -> bool:
        """
        Deletes an image at the given storage-relative path if it exists.

        Returns:
            bool: True if a file was deleted, False if none existed.
        """
        filename = cls._safe_relative_path(filename)
        fs = FileSystemStorage()
        if not fs.exists(filename):
            return False
        fs.delete(filename)
        return True

    @classmethod
    def get_url(cls, filename: str) -> str | None:
        """
        Builds the public URL for a previously saved image.

        Args:
            filename: Storage-relative path, e.g. "user/cover/<user_id>.png".

        Returns:
            str | None: The absolute URL, or None if no file exists there.
        """
        filename = cls._safe_relative_path(filename)
        fs = FileSystemStorage()
        if not fs.exists(filename):
            return None
        return f"{config('BE_DOMAIN_NAME')}{fs.url(filename)}"


class DateTimeUtils:
    """
    A utility class for handling date and time operations.

    """

    @staticmethod
    def get_current_utc_time() -> datetime.datetime:
        """
        Returns the current time in UTC.

        Returns:
            datetime.datetime: The current time in UTC.
        """
        local_now = datetime.datetime.now(pytz.timezone("UTC"))
        return DateTimeUtils.format_time(local_now)

    @staticmethod
    def format_time(date_time: datetime.datetime) -> datetime.datetime:
        """
        Formats a datetime object to the format '%Y-%m-%d %H:%M:%S'.

        Args:
            date_time (datetime.datetime): The datetime object to format.

        Returns:
            datetime.datetime: The formatted datetime object.
        """

        return date_time.replace(microsecond=0)

    @staticmethod
    def get_current_month_range():
        """Return (start, next_month_start) for the current UTC month.

        Both boundaries are at midnight so no karma is missed at the edges.
        Use __gte=start and __lt=next_month_start in queries (not __range,
        which is inclusive on both ends).

        Handles December correctly: rolls the year forward instead of
        wrapping month to 1 with the same year.
        """
        today = datetime.datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        start = today.replace(day=1)
        if today.month == 12:
            next_month = start.replace(year=today.year + 1, month=1)
        else:
            next_month = start.replace(month=today.month + 1)
        return start, next_month


class _CustomHTTPHandler:
    @staticmethod
    def get_client_ip_address(request):
        req_headers = request.META
        return (
            x_forwarded_for_value.split(",")[-1].strip()
            if (x_forwarded_for_value := req_headers.get("HTTP_X_FORWARDED_FOR"))
            else req_headers.get("REMOTE_ADDR")
        )


# (connect, read) seconds for outbound calls to partner APIs made on the request
# path. Without a timeout a slow partner holds the worker thread (and any open
# DB transaction) indefinitely.
EXTERNAL_REQUEST_TIMEOUT = (5, 30)


class _ExternalResponse:
    """A requests.Response whose JSON body has been parsed once, up front."""

    def __init__(self, response, payload):
        self._response = response
        self._payload = payload
        self.status_code = response.status_code
        self.content = response.content

    def json(self):
        return self._payload


def external_json_request(method, url, service_name, **kwargs):
    """
    requests.<method>(url, ...) with a timeout and error handling.

    Returns (response, None) on success, where response.json() returns the
    already-parsed body, or (None, failure CustomResponse) when the service
    cannot be reached, times out, or does not return JSON.
    """
    from utils.response import CustomResponse

    kwargs.setdefault("timeout", EXTERNAL_REQUEST_TIMEOUT)
    try:
        response = requests.request(method, url, **kwargs)
        payload = response.json()
    except requests.exceptions.Timeout:
        return None, CustomResponse(
            general_message=f"{service_name} did not respond in time. Please try again."
        ).get_failure_response()
    except (requests.exceptions.RequestException, ValueError):
        return None, CustomResponse(
            general_message=f"Could not get a valid response from {service_name}."
        ).get_failure_response()
    return _ExternalResponse(response, payload), None


logger = logging.getLogger(__name__)

# The bot reads one Discord message per sync, and a message holds 2,000 characters. 40 user ids
# (36 characters each, plus commas) keep a bulk-role message near 1,500, with room for the title.
BULK_ROLE_CHUNK = 40
WEBHOOK_ATTEMPTS = 3
WEBHOOK_MAX_WAIT = 5.0  # seconds; this runs on the request thread


def _retry_after(response) -> float:
    try:
        return float(response.json().get("retry_after", 1.0))
    except (ValueError, AttributeError, TypeError):
        try:
            return float(response.headers.get("Retry-After", 1.0))
        except (TypeError, ValueError):
            return 1.0


class DiscordWebhooks:
    @staticmethod
    def general_updates(category, action, *values) -> bool:
        """
        Send a sync message to the Discord bot's webhook channel. Returns True if Discord took it.

        A rejected or failed post is logged as an error. It used to be dropped silently: the
        status was never checked, so a message Discord refused (over 2,000 characters, or rate
        limited) never reached the bot while the dashboard reported success. A 429 is
        retried after the wait Discord asks for, bounded, because this runs on the request thread.
                Args:
        category(str): Category of webhook
        action(str): action of webhook
        values(str): values of webhook
        """
        content = f"{category}<|=|>{action}"
        for value in values:
            content = f"{content}<|=|>{value}"
        url = config("DISCORD_WEBHOOK_LINK", default="")
        if not url:
            return False
        for attempt in range(1, WEBHOOK_ATTEMPTS + 1):
            try:
                # (connect, read). This runs on the request thread, so a slow
                # Discord must not hold a worker for the old 30 seconds.
                response = requests.post(url, json={"content": content}, timeout=(3, 5))
            except requests.exceptions.RequestException:
                logger.exception("Discord sync %s %s failed to send", category, action)
                return False
            if 200 <= response.status_code < 300:
                return True
            if response.status_code == 429 and attempt < WEBHOOK_ATTEMPTS:
                time.sleep(min(_retry_after(response), WEBHOOK_MAX_WAIT))
                continue
            logger.error("Discord sync %s %s rejected: HTTP %s %s", category, action,
                         response.status_code, response.text[:200])
            return False
        return False

    @staticmethod
    def bulk_role_updates(action, role_title, user_ids) -> bool:
        """
        `bulk-role` sync for any number of users, sent as messages of at most BULK_ROLE_CHUNK ids.

        All ids used to go into one message; past about 53 users it exceeded Discord's
        2,000-character limit, so bulk assigns and removals never reached Discord.
        Returns True if every chunk was accepted. A durable queue should replace this later.
        """
        from utils.types import WebHookCategory  # utils.types imports nothing from this module

        ids = [str(user_id) for user_id in user_ids if user_id]
        accepted = True
        for start in range(0, len(ids), BULK_ROLE_CHUNK):
            chunk = ",".join(ids[start:start + BULK_ROLE_CHUNK])
            accepted = DiscordWebhooks.general_updates(
                WebHookCategory.BULK_ROLE.value, action, role_title, chunk) and accepted
        return accepted

class ImportCSV:
    def read_excel_file(self, file_obj):
        workbook = openpyxl.load_workbook(filename=io.BytesIO(file_obj.read()))
        sheet = workbook.active

        rows = []
        for row in sheet.iter_rows(values_only=True):
            row_dict = {
                header.value: cell_value for header, cell_value in zip(sheet[1], row)
            }
            rows.append(row_dict)
        workbook.close()

        return rows


def send_template_mail(
    context: dict, subject: str, address: list[str], attachment: str = None
):
    """
    The function `send_user_mail` sends an email to a user with the provided user data, subject, and
    address.

    :param context: A dictionary containing user data such as name, email, and any other relevant
    information
    :param subject: The subject of the email that will be sent to the user
    :param address: The `address` parameter is a list of strings that represents the path to the email
    template file. It is used to specify the location of the email template file that will be rendered
    and used as the content of the email
    attachment: The Attachment That send to the user
    """
    status = None

    email_content = render_to_string(
        f"mails/{'/'.join(map(str, address))}",
        {"user": context, "base_url": settings.FR_DOMAIN_NAME},
    )
    if not (mail := getattr(context, "email", None)):
        mail = context["email"]

    if attachment is None:
        return send_mail(
            subject=subject,
            message=email_content,
            from_email=settings.FROM_MAIL,
            recipient_list=[mail],
            html_message=email_content,
            fail_silently=False,
        )

    email = EmailMessage(
        subject=subject,
        body=email_content,
        from_email=settings.FROM_MAIL,
        to=[context["email"]],
    )

    # Handle different attachment formats
    if isinstance(attachment, tuple) and len(attachment) == 3:
        # Tuple format: (filename, content, mimetype) for binary attachments
        filename, content, mimetype = attachment
        email.attach(filename, content, mimetype)
    else:
        # Legacy format: file path or string
        email.attach(attachment)
    
    email.content_subtype = "html"
    return email.send()


def generate_code(char_count=6):
    characters = string.ascii_uppercase + string.digits
    code = "".join(random.choices(characters, k=char_count))
    return code

def get_user_mentor_profile(user_id):
    """
    Helper to fetch a user's UserMentor profile.
    """
    from db.user import UserMentor
    return UserMentor.objects.filter(user_id=user_id).first()
