"""validate_safe_url only: no DB, no HTTP."""
import pytest
from rest_framework.exceptions import ValidationError

from utils.validators import validate_safe_url


@pytest.mark.parametrize("url", [
    "https://github.com/user/repo",
    "https://github.com/user/repo#readme",            # '#' and ';' are fine here (validate_safe_text rejects them)
    "https://example.com/a;b?x=1&y=2",
    "https://sub.domain.co.in:8443/path",
    "HTTPS://GitHub.com/User/Repo",
    "https://xn--80ak6aa92e.com/",                     # punycode TLD-style host
    "  https://github.com/user/repo  ",                # trimmed
])
def test_accepts(url):
    assert validate_safe_url(url) == url.strip()


@pytest.mark.parametrize("url", [
    "",
    "   ",
    "javascript:alert(1)",
    "JavaScript://github.com/%0aalert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "file:///etc/passwd",
    "ftp://example.com/x",
    "http://github.com/user/repo",
    "github.com/user/repo",
    "//github.com/user/repo",
    "https://",
    "https:///path-only",
    "https://user:pass@github.com/",
    "https://@github.com/",
    "https://github.com@evil.com/",
    "https://evil.com\\@github.com/",
    "https:\\\\evil.com",
    "https://github.com/a b",
    "https://github.com/\tx",
    "https://github.com/\x00",
    "https://127.0.0.1/",
    "https://[::1]/",
    "https://[::1/",
    "https://2130706433/",
    "https://0x7f000001/",
    "https://127.1/",
    "https://localhost/",
    "https://intranet/",
    "https://github.com./",
    "https://github.com/" + "a" * 500,
])
def test_rejects(url):
    with pytest.raises(ValidationError):
        validate_safe_url(url)
