"""
Media content images: validate uploads, fetch remote URLs safely, resolve public URLs.

Ported from api/dashboard/events/event_image_utils.py so that the media_content
module is fully self-contained and does not depend on the events app.
"""
from __future__ import annotations

import ipaddress
import json
import os
import socket
import uuid
from io import BytesIO
from urllib.parse import urljoin, urlparse

import requests
from decouple import config
from django.conf import settings
from PIL import Image

MAX_BYTES = 5 * 1024 * 1024
ALLOWED_EXT = frozenset({'png', 'jpg', 'jpeg', 'gif', 'webp'})
FETCH_TIMEOUT = 15
MAX_REDIRECTS = 5

# PIL format -> file extension (stored in DB path)
_PIL_FORMAT_EXT = {
    'PNG': 'png',
    'JPEG': 'jpg',
    'GIF': 'gif',
    'WEBP': 'webp',
}


def _extension_from_filename(name: str) -> str:
    if not name or '.' not in name:
        return ''
    return name.rsplit('.', 1)[-1].lower()


def _validate_extension(ext: str) -> bool:
    return ext in ALLOWED_EXT


def _ensure_dir(subdir: str) -> str:
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'media_content', subdir)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def save_uploaded_image(upload, subdir: str) -> tuple[str | None, str | None]:
    """
    Save an uploaded file under MEDIA_ROOT/media_content/<subdir>/.
    Returns (relative_path, error_message).
    """
    ext = _extension_from_filename(getattr(upload, 'name', '') or '')
    if not _validate_extension(ext):
        return None, (
            f'Invalid image type. Allowed: {", ".join(sorted(ALLOWED_EXT))}'
        )
    if upload.size > MAX_BYTES:
        return None, 'File size exceeds 5MB limit'

    upload.seek(0)
    raw = upload.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        return None, 'File size exceeds 5MB limit'

    ext2, err = _validate_image_bytes(raw, ext)
    if err:
        return None, err
    final_ext = ext2 or ext

    unique = f'{uuid.uuid4()}.{final_ext}'
    upload_dir = _ensure_dir(subdir)
    rel = f'media_content/{subdir}/{unique}'
    abs_path = os.path.join(upload_dir, unique)
    with open(abs_path, 'wb+') as dest:
        dest.write(raw)
    return rel, None


def _validate_image_bytes(data: bytes, filename_ext: str) -> tuple[str | None, str | None]:
    """Returns (canonical_ext or None, error)."""
    try:
        img = Image.open(BytesIO(data))
        img.verify()
    except Exception:
        return None, 'Invalid or corrupted image file'

    try:
        img = Image.open(BytesIO(data))
        fmt = (img.format or '').upper()
        pil_ext = _PIL_FORMAT_EXT.get(fmt)
        if not pil_ext:
            return None, 'Unsupported image format'
        if not _validate_extension(pil_ext):
            return None, 'Unsupported image format'
        if filename_ext and filename_ext != pil_ext and not (
            filename_ext == 'jpeg' and pil_ext == 'jpg'
        ):
            return pil_ext, None
        return pil_ext, None
    except Exception:
        return None, 'Invalid or corrupted image file'


def _hostname_is_blocked(hostname: str) -> bool:
    if not hostname:
        return True
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except OSError:
        return True
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return True
        if ip.version == 6 and ip in ipaddress.ip_network('fc00::/7'):
            return True
    return False


def _url_is_safe_for_fetch(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False
    if not parsed.hostname:
        return False
    if '@' in parsed.netloc:
        return False
    return not _hostname_is_blocked(parsed.hostname)


def try_normalize_media_url_to_relative(url: str) -> str | None:
    """If url points at this deployment's MEDIA_URL, return stored relative path."""
    u = (url or '').strip()
    if not u.startswith(('http://', 'https://')):
        return None
    base = config('BE_DOMAIN_NAME', default='').rstrip('/')
    if not base:
        return None
    prefix = f'{base}{settings.MEDIA_URL}'.rstrip('/') + '/'
    if u.startswith(prefix):
        return u[len(prefix):].lstrip('/')
    return None


def fetch_image_from_url(url: str, subdir: str) -> tuple[str | None, str | None]:
    """
    Download an image from a remote URL with SSRF checks and size limits.
    Returns (relative_path, error_message).
    """
    u = (url or '').strip()
    if not u:
        return None, 'Empty image URL'

    normalized = try_normalize_media_url_to_relative(u)
    if normalized:
        return normalized, None

    if not u.startswith(('http://', 'https://')):
        # Relative path or opaque string — store as-is (legacy)
        return u, None

    current = u
    session = requests.Session()
    for _ in range(MAX_REDIRECTS + 1):
        if not _url_is_safe_for_fetch(current):
            return None, 'URL is not allowed'
        try:
            resp = session.get(
                current,
                timeout=FETCH_TIMEOUT,
                stream=True,
                allow_redirects=False,
                headers={'User-Agent': 'mulearnbackend-media-image/1.0'},
            )
        except requests.RequestException as exc:
            return None, f'Failed to download image: {exc}'

        if resp.status_code in (301, 302, 303, 307, 308):
            loc = resp.headers.get('Location')
            if not loc:
                return None, 'Redirect without Location header'
            current = urljoin(current, loc)
            continue

        if resp.status_code != 200:
            return None, f'Failed to download image (HTTP {resp.status_code})'

        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_BYTES:
                return None, 'Downloaded file exceeds 5MB limit'
            chunks.append(chunk)
        data = b''.join(chunks)
        break
    else:
        return None, 'Too many redirects'

    ctype = (resp.headers.get('Content-Type') or '').split(';')[0].strip().lower()
    if ctype and not ctype.startswith('image/'):
        return None, 'URL did not return an image'

    ext_guess = 'jpg'
    if 'png' in ctype:
        ext_guess = 'png'
    elif 'jpeg' in ctype or 'jpg' in ctype:
        ext_guess = 'jpg'
    elif 'gif' in ctype:
        ext_guess = 'gif'
    elif 'webp' in ctype:
        ext_guess = 'webp'

    ext2, err = _validate_image_bytes(data, ext_guess)
    if err:
        return None, err
    final_ext = ext2 or ext_guess

    unique = f'{uuid.uuid4()}.{final_ext}'
    upload_dir = _ensure_dir(subdir)
    rel = f'media_content/{subdir}/{unique}'
    abs_path = os.path.join(upload_dir, unique)
    with open(abs_path, 'wb+') as dest:
        dest.write(data)
    return rel, None


def delete_stale_media(old_path: str | None, new_path: str | None) -> None:
    """Remove a previously stored file under media_content/ when replaced."""
    if not old_path or old_path == new_path:
        return
    if not old_path.startswith('media_content/'):
        return
    full = os.path.join(settings.MEDIA_ROOT, old_path.replace('/', os.sep))
    if os.path.isfile(full):
        try:
            os.remove(full)
        except OSError:
            pass


def resolve_image_url(value: str | None, request=None) -> str | None:
    """
    Build an absolute URL for API responses.
    Relative paths under media get BE_DOMAIN_NAME + MEDIA_URL; existing http(s) left as-is.
    """
    if not value:
        return None
    v = value.strip()
    if not v:
        return None
    if v.startswith('http://') or v.startswith('https://'):
        return v
    base = config('BE_DOMAIN_NAME', default='').rstrip('/')
    path = v.lstrip('/')
    rel_url = f'{settings.MEDIA_URL.rstrip("/")}/{path}'
    if base:
        return f'{base}{rel_url}'
    if request:
        return request.build_absolute_uri(rel_url)
    return rel_url


def _querydict_to_plain_dict(data) -> dict:
    """Single-value snapshot of QueryDict / dict for serializer input."""
    out = {}
    try:
        keys = getattr(data, 'keys', lambda: [])()
        for k in keys:
            out[k] = data.get(k)
    except Exception:
        out = dict(data) if hasattr(data, 'items') else {}
    return out


def merge_media_write_payload(
    request,
    *,
    partial: bool,
    image_fields: tuple[tuple[str, str], ...] = (('poster_thumbnail', 'posters'),),
) -> tuple[dict | None, str | None]:
    """
    Merge multipart/JSON body with resolved image paths.

    For each (field, subdir) pair in image_fields:
      - If the field is present in request.FILES, validate and save the upload.
      - If the field is present in request.data as a URL, fetch and save the remote image.
      - If partial=True and the field is absent, leave it untouched.

    Returns (payload_dict, error_message).
    """
    payload = _querydict_to_plain_dict(request.data)

    for field, subdir in image_fields:
        upload = request.FILES.get(field)
        if upload:
            rel, err = save_uploaded_image(upload, subdir)
            if err:
                return None, err
            payload[field] = rel
            continue

        if partial:
            has_key = field in request.data
            if not has_key:
                payload.pop(field, None)
                continue
        else:
            has_key = field in request.data
            if not has_key:
                continue

        raw = request.data.get(field)
        if raw is None:
            payload[field] = None
            continue
        if isinstance(raw, str):
            raw = raw.strip()
        if raw == '' or raw is None:
            payload[field] = None
            continue

        if not isinstance(raw, str):
            payload[field] = raw
            continue

        normalized = try_normalize_media_url_to_relative(raw)
        if normalized:
            payload[field] = normalized
            continue

        if raw.lower().startswith(('http://', 'https://')):
            rel, err = fetch_image_from_url(raw, subdir)
            if err:
                return None, err
            payload[field] = rel
        else:
            payload[field] = raw

    return payload, None
