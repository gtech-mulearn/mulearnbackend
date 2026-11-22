#!/usr/bin/env bash
# Running tests
# -------------
#   scripts/test.sh [pytest arguments or paths]
#       The SQLite tier: an in-memory database, never a real one, whatever .env says.
#       Runs every test not marked @pytest.mark.mysql.
#   scripts/test.sh --mysql [pytest arguments or paths]
#       The MySQL tier: tests marked @pytest.mark.mysql, against a local test database.
#       Set TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME, TEST_DB_USER and TEST_DB_PASSWORD to change
#       the defaults (127.0.0.1, 3306, test_mulearn, root, local-only).
#       SYSTEM_ADMIN_ID is the system user scripts/seed-system-user.sql creates
#       (00000000-0000-4000-8000-000000000001); set TEST_SYSTEM_ADMIN_ID to change it.
#
# Paths are relative to the repository root. PYTHON picks the interpreter (default: python).
# The guard in tests/db_guard.py refuses any database that isn't SQLite or a local test_ database.
# See docs/architecture/12-testing-and-quality-gates.md.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PYTHON="${PYTHON:-python}"

if [ ! -f .env ]; then
    echo "No .env found: copy .env.sample to .env first." >&2
    exit 1
fi
if ! "$PYTHON" -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('pytest') else 1)"; then
    echo "pytest isn't installed for $PYTHON: run pip install pytest." >&2
    exit 1
fi

# The logging settings fail at startup if the log directory is missing.
log_dir="${LOGGER_DIR_PATH:-}"
if [ -z "$log_dir" ]; then
    log_dir="$(sed -n 's/^[[:space:]]*LOGGER_DIR_PATH[[:space:]]*=[[:space:]]*//p' .env | tail -n 1 | tr -d '\r')"
    log_dir="${log_dir%\"}"; log_dir="${log_dir#\"}"; log_dir="${log_dir%\'}"; log_dir="${log_dir#\'}"
fi
mkdir -p "${log_dir:-./logs}"

# Exported variables win over .env, because decouple reads the environment first.
if [ "${1:-}" = "--mysql" ]; then
    shift
    export DATABASE_ENGINE=django.db.backends.mysql
    export DATABASE_HOST="${TEST_DB_HOST:-127.0.0.1}"
    export DATABASE_PORT="${TEST_DB_PORT:-3306}"
    export DATABASE_NAME="${TEST_DB_NAME:-test_mulearn}"
    export DATABASE_USER="${TEST_DB_USER:-root}"
    export DATABASE_PASSWORD="${TEST_DB_PASSWORD:-local-only}"
    # The backend won't start without this user (db/apps.py). It must match scripts/seed-system-user.sql.
    export SYSTEM_ADMIN_ID="${TEST_SYSTEM_ADMIN_ID:-00000000-0000-4000-8000-000000000001}"
    "$PYTHON" scripts/check_test_mysql.py
    exec "$PYTHON" -m pytest "$@" --import-mode=importlib -m mysql
fi

export DATABASE_ENGINE=django.db.backends.sqlite3
export DATABASE_NAME=:memory:
export DATABASE_USER= DATABASE_PASSWORD= DATABASE_HOST= DATABASE_PORT=
exec "$PYTHON" -m pytest "$@" --import-mode=importlib -m "not mysql"
