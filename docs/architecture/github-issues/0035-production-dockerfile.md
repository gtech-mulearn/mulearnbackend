# Build a multi-stage, non-root image

| | |
|---|---|
| ID | 0035 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | platform |
| Size | M |
| Labels | arch, phase:2, module:platform, type:chore, size:M |
| Depends on | 0011, 0032, 0033 |
| Blocks | 0036 |
| Repos | mulearnbackend |

## Why

The image is built on the host from `python:3.10-slim-buster`, a base past its support date, running as root with build tools inside. A multi-stage, non-root image on a supported base is smaller and safer ([10-infrastructure-and-deployment.md](../10-infrastructure-and-deployment.md#containers)).

## Before you start

- Issue 0011 must be merged.
- Read the current `Dockerfile` and `.dockerignore` (if any).
- Issues 0032 and 0033 must also be merged.

## What to do

1. Rewrite the `Dockerfile` as two stages:
   - **builder:** a supported Debian base with Python 3.10 (`python:3.10-slim-bookworm`; the Python upgrade comes later). It installs `build-essential`, `default-libmysqlclient-dev` and `pkg-config`, and builds wheels for `requirements.txt`;
   - **runtime:** the same base, installing only the runtime MySQL client library and the wheels. It runs as user `app` (uid 10001) with `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1`.
2. Add a `HEALTHCHECK` on `/healthz/live`.
3. Set the default `CMD` to gunicorn with `gunicorn.conf.py`.
4. Add `.dockerignore`, excluding `.git`, `venv`, `.venv`, `docs`, `tests`, `__pycache__`, `logs` and `*.pyc`.
5. In CI, build the image and run `docker run --rm <image> python -c "import django"`.

## Acceptance criteria

- [ ] The image builds in CI.
- [ ] `docker run --rm <image> id -u` prints `10001`.
- [ ] The image is smaller than the current one; note both sizes in the pull request.

## How to test

Build locally with `docker build -t mulearn:local .`, then run `docker run --rm mulearn:local id -u`.

## Out of scope

- Pushing images (issue 0036).
- Changing the Python version.

## Notes for reviewers

Check that nothing in the runtime stage needs root, for example writing into `logs/`. Point log output to stdout.
