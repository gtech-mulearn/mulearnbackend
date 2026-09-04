"""
Event cover/banner images: validate uploads, fetch remote URLs safely, resolve public URLs.
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
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'events', subdir)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def save_uploaded_event_image(upload, subdir: str) -> tuple[str | None, str | None]:
    """
    Save an uploaded file under MEDIA_ROOT/events/<subdir>/.
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
    rel = f'events/{subdir}/{unique}'
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
        # Filename should match actual content when possible
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
        return u[len(prefix) :].lstrip('/')
    return None


def fetch_event_image_from_url(url: str, subdir: str) -> tuple[str | None, str | None]:
    """
    Download an image from a remote URL with SSRF checks and size limits.
    Returns (relative_path, error_message).
    """
    u = (url or '').strip()
    if not u:
        return None, 'Empty image URL'

    normalized = try_normalize_media_url_to_relative(u)
    if normalized:
        if normalized.startswith(f'events/{subdir}/'):
            return normalized, None
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
                headers={'User-Agent': 'mulearnbackend-event-image/1.0'},
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
    rel = f'events/{subdir}/{unique}'
    abs_path = os.path.join(upload_dir, unique)
    with open(abs_path, 'wb+') as dest:
        dest.write(data)
    return rel, None


def delete_stale_event_media(old_path: str | None, new_path: str | None) -> None:
    """Remove a previously stored file under events/ when replaced."""
    if not old_path or old_path == new_path:
        return
    if not old_path.startswith('events/'):
        return
    full = os.path.join(settings.MEDIA_ROOT, old_path.replace('/', os.sep))
    if os.path.isfile(full):
        try:
            os.remove(full)
        except OSError:
            pass


def delete_event_media_paths(paths) -> None:
    """Remove files this request wrote to disk that never ended up committed.

    save_uploaded_event_image / fetch_event_image_from_url write to
    MEDIA_ROOT before the caller has validated the rest of the payload or
    saved the row, so a failure anywhere after that point (validation, a
    permission check, a rolled-back transaction) must not leave the file
    behind with nothing in the DB pointing at it.
    """
    for path in paths:
        if not path or not path.startswith('events/'):
            continue
        full = os.path.join(settings.MEDIA_ROOT, path.replace('/', os.sep))
        if os.path.isfile(full):
            try:
                os.remove(full)
            except OSError:
                pass


def resolve_event_image_url(value: str | None, request=None) -> str | None:
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


def merge_event_write_payload(request, *, partial: bool, event=None) -> tuple[dict | None, list[str], str | None]:
    """
    Merge multipart/JSON body with resolved cover_image / banner_image paths.
    Returns (payload_dict, new_media_paths, error_message).

    `new_media_paths` lists any cover_image/banner_image paths this call
    wrote to disk (upload or remote fetch) — as opposed to a path merely
    passed through unchanged. If the caller doesn't end up committing this
    payload (validation fails, a permission check rejects it, the save
    rolls back), it must pass these to delete_event_media_paths() so the
    file doesn't orphan under MEDIA_ROOT with nothing in the DB pointing at it.
    """
    payload = _querydict_to_plain_dict(request.data)
    new_media_paths: list[str] = []

    if 'tags' in payload and isinstance(payload['tags'], str):
        raw_tags = payload['tags'].strip()
        if not raw_tags:
            payload['tags'] = None
        else:
            try:
                payload['tags'] = json.loads(raw_tags)
            except json.JSONDecodeError:
                return None, new_media_paths, 'Invalid JSON for tags'

    for field, subdir in (
        ('cover_image', 'covers'),
        ('banner_image', 'banners'),
    ):
        upload = request.FILES.get(field)
        if upload:
            rel, err = save_uploaded_event_image(upload, subdir)
            if err:
                return None, new_media_paths, err
            payload[field] = rel
            new_media_paths.append(rel)
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
            rel, err = fetch_event_image_from_url(raw, subdir)
            if err:
                return None, new_media_paths, err
            payload[field] = rel
            new_media_paths.append(rel)
        else:
            payload[field] = raw

    return payload, new_media_paths, None
