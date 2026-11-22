"""Pre-flight for the MySQL test tier, run by scripts/test.sh and scripts/test.ps1 before pytest.

It applies the same guard as the test suite (tests/db_guard.py), so a database that isn't
a local test database is refused, then checks that the server answers, so a missing
server fails in seconds with a hint instead of hanging.
Exit codes: 0 ready, 1 can't reach the server, 2 refused by the guard.
"""

import os
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _pytest.outcomes import Exit  # noqa: E402

from tests.db_guard import assert_safe_test_database  # noqa: E402

TIMEOUT_SECONDS = 5


def main(env: dict) -> int:
    host = env.get("DATABASE_HOST", "")
    port = env.get("DATABASE_PORT", "") or "3306"
    try:
        assert_safe_test_database(
            {"ENGINE": env.get("DATABASE_ENGINE", ""), "HOST": host, "NAME": env.get("DATABASE_NAME", "")}
        )
    except Exit as refused:
        print(refused.msg, file=sys.stderr)
        return 2
    try:
        socket.create_connection((host or "127.0.0.1", int(port)), timeout=TIMEOUT_SECONDS).close()
    except OSError as error:
        print(
            f"Can't reach MySQL at {host or '127.0.0.1'}:{port} ({error}). "
            "Start the local test database first (docker compose, see DEVELOPMENT.md).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(dict(os.environ)))
