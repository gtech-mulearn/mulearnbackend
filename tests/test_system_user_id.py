import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def seeded_id():
    seed = (ROOT / "scripts" / "seed-system-user.sql").read_text(encoding="utf-8")
    return re.search(r"VALUES \('([0-9a-f-]{36})'", seed).group(1)


@pytest.mark.parametrize("path", ["scripts/test.sh", "scripts/test.ps1", ".env.local.example"])
def test_the_seeded_system_user_is_the_configured_one(path):
    # The backend won't start on the MySQL tier, or locally, if these ids differ.
    text = (ROOT / path).read_text(encoding="utf-8")

    assert "SYSTEM_ADMIN_ID" in text
    assert seeded_id() in text
