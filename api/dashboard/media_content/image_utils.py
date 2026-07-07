"""
Media content images: validate uploads, fetch remote URLs safely, resolve public URLs.

Ported from api/dashboard/events/event_image_utils.py so that the media_content
module is fully self-contained and does not depend on the events app.
"""
from __future__ import annotations

import ipaddress
import os
import socket
import threading
import uuid
from io import BytesIO
from urllib.parse import urljoin, urlparse

import requests
import requests.adapters
import urllib3
import urllib3.util.connection
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
    """Return True if *all* resolved IPs for hostname are non-routable/private.

    This is intentionally strict: if *any* resolved address is in a
    disallowed range we block the whole hostname.
    """
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


# Thread-local storage used by _SSRFBlockingAdapter to pass the pre-validated
# IP to our patched create_connection without touching global state.
_ssrf_local = threading.local()

# Keep a reference to the real urllib3 create_connection so we can call it
# after substituting the resolved (and validated) IP address.
_real_create_connection = urllib3.util.connection.create_connection


def _pinned_create_connection(address, *args, **kwargs):
    """
    Drop-in replacement for ``urllib3.util.connection.create_connection``.

    When ``_ssrf_local.pinned_ip`` is set by ``_SSRFBlockingAdapter.send``
    for the current thread, the hostname in *address* is silently replaced
    with the pre-validated IP so urllib3 connects to that address directly
    instead of re-resolving DNS.  The original hostname is preserved in the
    URL, so urllib3 still uses it for TLS SNI and certificate verification.

    Outside of an ``_SSRFBlockingAdapter`` call the function is transparent.
    """
    pinned_ip = getattr(_ssrf_local, 'pinned_ip', None)
    if pinned_ip is not None:
        host, port = address
        address = (pinned_ip, port)
    return _real_create_connection(address, *args, **kwargs)


# Patch once at import time.  This is the same technique used by the
# ``responses`` test library and various urllib3 extension packages.
urllib3.util.connection.create_connection = _pinned_create_connection
# urllib3 imports create_connection into the connection module's namespace too.
urllib3.connection.HTTPConnection.is_verified  # ensure module is imported
import urllib3.connection as _urllib3_connection  # noqa: E402
_urllib3_connection.create_connection = _pinned_create_connection


class _SSRFBlockingAdapter(requests.adapters.HTTPAdapter):
    """
    A requests transport adapter that closes the DNS-rebinding window.

    Standard SSRF guards resolve the hostname once for the IP check and
    then let the OS resolver re-resolve it when the socket is opened —
    leaving a TOCTOU window.  This adapter eliminates that gap by:

    1. Resolving the hostname to an IP via ``socket.getaddrinfo``.
    2. Validating the resolved IP with ``_hostname_is_blocked``.
    3. Pinning the TCP connection to that IP at the socket layer so
       urllib3 never performs a second DNS lookup.

    Crucially, the request URL is **not** rewritten.  urllib3 therefore
    derives ``server_hostname`` from the original hostname, which means
    TLS SNI is sent correctly and the server certificate is verified
    against the hostname — not against a raw IP literal that almost no
    CDN certificate covers.
    """

    def send(self, request, **kwargs):
        parsed = urlparse(request.url)
        hostname = parsed.hostname
        port = parsed.port

        if not hostname:
            raise requests.exceptions.InvalidURL('Missing hostname in URL')

        # Resolve once, validate once — the actual connection uses this IP.
        try:
            infos = socket.getaddrinfo(
                hostname,
                port,
                type=socket.SOCK_STREAM,
            )
        except OSError as exc:
            raise requests.exceptions.ConnectionError(
                f'DNS resolution failed for {hostname!r}: {exc}'
            ) from exc

        if not infos:
            raise requests.exceptions.ConnectionError(
                f'DNS resolution returned no results for {hostname!r}'
            )

        ip_str = infos[0][4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError as exc:
            raise requests.exceptions.ConnectionError(
                f'Unparseable IP address {ip_str!r} for {hostname!r}'
            ) from exc

        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_reserved
            or ip_obj.is_multicast
            or (ip_obj.version == 6 and ip_obj in ipaddress.ip_network('fc00::/7'))
        ):
            raise requests.exceptions.ConnectionError(
                f'URL resolves to a blocked address ({ip_str})'
            )

        # Inject the pre-validated IP into the thread-local so that
        # _pinned_create_connection uses it instead of re-resolving DNS.
        # The URL itself is left unchanged so that urllib3's TLS layer
        # sends the correct SNI extension and verifies the certificate
        # against the original hostname.
        _ssrf_local.pinned_ip = ip_str
        try:
            return super().send(request, **kwargs)
        finally:
            # Always clear the pin, even on exception, to avoid leaking
            # state into unrelated requests on the same thread.
            _ssrf_local.pinned_ip = None


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
    # Mount the SSRF-blocking adapter for both schemes.  It resolves DNS
    # exactly once per redirect hop, validates the IP, and pins the
    # socket to that address — closing the DNS-rebinding TOCTOU window.
    _adapter = _SSRFBlockingAdapter()
    session.mount('http://', _adapter)
    session.mount('https://', _adapter)

    for _ in range(MAX_REDIRECTS + 1):
        # Fast-path structural check (scheme, credentials in netloc).
        # The adapter enforces the IP-level block at connect time.
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
        except requests.ConnectionError:
            return None, 'URL is not allowed'
        except requests.RequestException:
            return None, 'Failed to download image: connection error'

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
    skip_remote_fetch: bool = False,
) -> tuple[dict | None, str | None, dict[str, tuple[str, str]]]:
    """
    Merge multipart/JSON body with resolved image paths.

    For each (field, subdir) pair in image_fields:
      - If the field is present in request.FILES, validate and save the upload.
      - If the field is present in request.data as a URL:
          * When skip_remote_fetch=False (default): fetch the remote image
            synchronously and store the resulting relative path.
          * When skip_remote_fetch=True: leave the field as None in the
            payload and report the pending URL in pending_url_fields so the
            caller can dispatch a Celery task instead of blocking the worker.
      - If partial=True and the field is absent, leave it untouched.

    Returns (payload_dict, error_message, pending_url_fields).
    pending_url_fields maps field -> (raw_url, subdir) for every remote URL
    that was deferred when skip_remote_fetch=True.
    """
    payload = _querydict_to_plain_dict(request.data)
    pending_url_fields: dict[str, tuple[str, str]] = {}

    for field, subdir in image_fields:
        upload = request.FILES.get(field)
        if upload:
            rel, err = save_uploaded_image(upload, subdir)
            if err:
                return None, err, {}
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
            if skip_remote_fetch:
                # Defer the download to a Celery task; the field is stored
                # as None until the task completes.
                payload[field] = None
                pending_url_fields[field] = (raw, subdir)
            else:
                rel, err = fetch_image_from_url(raw, subdir)
                if err:
                    return None, err, {}
                payload[field] = rel
        else:
            payload[field] = raw

    return payload, None, pending_url_fields
