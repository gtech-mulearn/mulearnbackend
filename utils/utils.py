import csv
import datetime
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
    ) -> QuerySet:
        """
        Returns a paginated queryset based on the provided parameters.

        Args:
            - queryset (QuerySet): The original queryset to be paginated.
            - request: The request object containing query parameters.
            - search_fields (list): The list of fields to search for.
            - sort_fields (dict, optional): A dictionary mapping sort fields. Defaults to None.
            - is_pagination (bool, optional): Flag indicating whether pagination should be applied. Defaults to True.

        Returns:
            - QuerySet or dict: The paginated queryset or a dictionary containing the paginated queryset and pagination information.
        """
        if sort_fields is None:
            sort_fields = {}

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

            queryset = queryset.filter(query)

        if sort_by:
            sort = sort_by[1:] if sort_by.startswith("-") else sort_by
            if sort_field_name := sort_fields.get(sort):
                if sort_by.startswith("-"):
                    sort_field_name = f"-{sort_field_name}"

                # "pk" tiebreak: the requested field alone is rarely unique
                # (e.g. many rows share a start_datetime or a status), so
                # without it, rows tied on sort_field_name can be returned in
                # a different relative order between requests, causing
                # offset-paginated clients to skip or see duplicate rows
                # across pages.
                queryset = queryset.order_by(sort_field_name, "pk")
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
    def get_start_and_end_of_previous_month():
        today = DateTimeUtils.get_current_utc_time()
        start_date = today.replace(day=1)
        end_date = start_date.replace(
            day=1, month=start_date.month % 12 + 1
        ) - timedelta(days=1)
        return start_date, end_date


class _CustomHTTPHandler:
    @staticmethod
    def get_client_ip_address(request):
        req_headers = request.META
        return (
            x_forwarded_for_value.split(",")[-1].strip()
            if (x_forwarded_for_value := req_headers.get("HTTP_X_FORWARDED_FOR"))
            else req_headers.get("REMOTE_ADDR")
        )


class DiscordWebhooks:
    @staticmethod
    def general_updates(category, action, *values) -> str:
        """
        Modify channels and category in Discord
                Args:
        category(str): Category of webhook
        action(str): action of webhook
        values(str): values of webhook
        """
        content = f"{category}<|=|>{action}"
        for value in values:
            content = f"{content}<|=|>{value}"
        url = config("DISCORD_WEBHOOK_LINK", default="")
        if url:
            data = {"content": content}
            requests.post(url, json=data)


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
