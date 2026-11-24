# Lock dependencies with hashes and remove unused packages

| | |
|---|---|
| ID | 0039 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | platform |
| Size | M |
| Labels | arch, phase:2, module:platform, type:chore, size:M |
| Depends on | 0011 |
| Blocks | 0040 |
| Repos | mulearnbackend |

## Why

`requirements.txt` pins top-level packages but not their dependencies, has no hashes, and includes packages that are installed but never imported (`djangorestframework-simplejwt`), plus two MySQL drivers (`mysqlclient` and `pymysql`). Locked, hashed dependencies make builds reproducible ([ADR-050](../adr/ADR-050-platform-versions.md), [ADR-051](../adr/ADR-051-toolchain.md)).

## Before you start

- Issue 0011 must be merged.

## What to do

1. Confirm with `git grep` that `rest_framework_simplejwt` and `pymysql` aren't imported anywhere (including `import pymysql; pymysql.install_as_MySQLdb()`). If one is used, keep it and say so.
2. Remove the unused packages from `requirements.txt`.
3. Generate `requirements.lock` with hashes, using `uv pip compile --generate-hashes requirements.txt -o requirements.lock`.
4. Make the Dockerfile and CI install from `requirements.lock` with `--require-hashes`.
5. Add Renovate or Dependabot configuration for weekly update pull requests.

## Acceptance criteria

- [ ] CI installs from the lock file with hashes.
- [ ] The app starts and both test tiers pass.
- [ ] Removed packages are listed, with the evidence that they were unused.

## How to test

```sh
scripts/test.sh tests/
```

## Out of scope

- Upgrading any package (issues 0040 and 0042).

## Notes for reviewers

Check the grep evidence for each removed package.
