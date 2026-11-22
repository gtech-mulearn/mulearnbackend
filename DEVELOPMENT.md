# Developing the μLearn backend

## Prerequisites

- **Python 3.10.**
- **The MySQL client headers `mysqlclient` needs:**
  - Debian or Ubuntu: `sudo apt-get install default-libmysqlclient-dev pkg-config build-essential`;
  - macOS: `brew install mysql-client pkg-config`;
  - Windows: the `mysqlclient` wheel installs without them.
- **Docker with Compose,** to run the whole backend locally. You don't need it to run the tests.

## Set up a clone

```sh
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.sample .env
pre-commit install                     # optional: ruff on every commit
```

`.env` is read by the commands you run on your machine. The test runner below overrides every database setting in it, so the other values only need to be present.

## Run the tests

> **Never run `pytest` directly against a configured database.** Some legacy tests flush every table of the database they run against. Always use the runner. The guard in `tests/db_guard.py` stops pytest for anything but SQLite or a local database whose name starts with `test_`.

```sh
scripts/test.sh tests/          # the unit tier, as CI runs it: in-memory SQLite, whatever .env says
scripts/test.sh <paths>         # any tests, on the same SQLite tier
scripts/test.sh --mysql <paths> # tests marked @pytest.mark.mysql, against the local test_mulearn database
```

- **On Windows PowerShell,** use `scripts\test.ps1`, with `-Mysql` in place of `--mysql`.
- **The MySQL tier** connects to `127.0.0.1:3306`, database `test_mulearn`, as `root` with password `local-only`, which is the local environment below. Set `TEST_DB_HOST`, `TEST_DB_PORT`, `TEST_DB_NAME`, `TEST_DB_USER` or `TEST_DB_PASSWORD` to change them. If nothing is listening, it fails within seconds with a connection error.
- **The whole legacy suite (`scripts/test.sh` with no paths)** has known failures under SQLite today. Issue 0013 adds a baseline so CI checks it too. `scripts/test.sh tests/` must stay green.

## Run the whole backend locally

```sh
cp .env.local.example .env.local
docker compose -f docker-compose.local.yml up -d
curl -s localhost:8000/api/v1/public/global-count/
```

- **The first start builds MySQL from `schema/latest.sql`,** into both `mulearn` and `test_mulearn`, and seeds the system user the backend needs at startup.
- **The services** are `mysql`, `redis-cache`, `redis-state`, `web` (http://localhost:8000), `worker` and `beat`. Ports are published on `127.0.0.1` only.
- **Containers read `.env.local`;** commands on your machine read `.env`. Both are ignored by git.
- **To stop,** run `docker compose -f docker-compose.local.yml down`. To start again from an empty database, add `-v`, which deletes the database volume.

## Troubleshooting

- **`SystemUserNotFoundError: Create a System User with pk -"…"`.** The database has no user whose id is `SYSTEM_ADMIN_ID`.
  - In the local environment, `SYSTEM_ADMIN_ID` in `.env.local` must match the id in `scripts/seed-system-user.sql`. Restore it, or rebuild the database with `down -v` and then `up -d`.
  - Against another database, create that user there first.
- **Port 3306 is already in use.** Another MySQL is running on your machine. Start with `LOCAL_MYSQL_PORT=3307 docker compose -f docker-compose.local.yml up -d`, and test with `TEST_DB_PORT=3307 scripts/test.sh --mysql`.
- **Port 8000 is already in use.** Stop the other server, or change the `web` port mapping in your local copy of the compose file.
- **`ImproperlyConfigured: Missing required settings: …` at startup.** Add those names to `.env` (compare with `.env.sample`), or to `.env.local` (compare with `.env.local.example`).
- **`Refusing to run tests against database …`.** pytest was pointed at a database that isn't a local `test_` one. Use `scripts/test.sh`.
- **`ERROR 1674 … unsafe because it uses a system function` while loading `schema/latest.sql` yourself.** Turn binary logging off for that session (see `schema/README.md`).
- **The logs directory is missing.** The logging settings write to `LOGGER_DIR_PATH` (`./logs` in `.env.sample`). `scripts/test.sh` creates it; for `manage.py`, run `mkdir logs` first.
