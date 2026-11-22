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
pip install --require-hashes -r requirements-dev.lock
cp .env.sample .env
pre-commit install                     # optional: ruff on every commit
```

`.env` is read by the commands you run on your machine. The test runner below overrides every database setting in it, so the other values only need to be present.

## Change a dependency

`requirements.txt` and `requirements-dev.txt` hold the direct dependencies, pinned. The lock files pin every package, transitive ones included, with hashes:

- `requirements.lock`, which the Docker image installs;
- `requirements-dev.lock`, which CI and local setups install. It includes everything in `requirements.lock`, at the same versions.

After editing a requirements file, regenerate both, using the commands in their headers, and commit all four files:

```sh
pip install uv
uv pip compile --universal --python-version 3.10 --generate-hashes requirements.txt -o requirements.lock
uv pip compile --universal --python-version 3.10 --generate-hashes requirements.txt requirements-dev.txt -c requirements.lock -o requirements-dev.lock
```

`tests/test_requirements_lock.py` fails when a pin and its lock disagree. Dependabot opens weekly pull requests that update the pins; regenerate the locks in the same pull request.

## Run the tests

> **Never run `pytest` directly against a configured database.** Some legacy tests flush every table of the database they run against. Always use the runner. The guard in `tests/db_guard.py` stops pytest for anything but SQLite or a local database whose name starts with `test_`.

```sh
scripts/test.sh tests/          # the unit tier, as CI runs it: in-memory SQLite, whatever .env says
scripts/test.sh <paths>         # any tests, on the same SQLite tier
scripts/test.sh --mysql <paths> # tests marked @pytest.mark.mysql, against the local test_mulearn database
```

- **On Windows PowerShell,** use `scripts\test.ps1`, with `-Mysql` in place of `--mysql`.
- **The MySQL tier** connects to `127.0.0.1:3306`, database `test_mulearn`, as `root` with password `local-only`, which is the local environment below. Set `TEST_DB_HOST`, `TEST_DB_PORT`, `TEST_DB_NAME`, `TEST_DB_USER` or `TEST_DB_PASSWORD` to change them. If nothing is listening, it fails within seconds with a connection error.
  - Tests run against `test_mulearn` as it was loaded; no `test_test_mulearn` is created.
  - `SYSTEM_ADMIN_ID` is set to the system user that `scripts/seed-system-user.sql` creates, whatever `.env` says. Set `TEST_SYSTEM_ADMIN_ID` to change it.
  - [tests/README.md](tests/README.md) says which tests belong on this tier.
- **The whole legacy suite (`scripts/test.sh` with no paths)** has known failures under SQLite today. They're listed in `tests/legacy_baseline.txt`, and the `ci / legacy` check fails only on a failure that isn't listed. Check it locally the same way:

  ```sh
  scripts/test.sh --junitxml=legacy.xml
  python scripts/legacy_ratchet.py legacy.xml
  ```

  The baseline only shrinks. When the ratchet reports that a baseline test no longer fails, delete its line. Never add a line: fix the test. `scripts/test.sh tests/` must stay green.

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
