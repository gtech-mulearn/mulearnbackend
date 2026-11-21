# Run the unit test tier and ruff on every pull request

| | |
|---|---|
| ID | 0011 |
| Phase / milestone | Phase 1: Foundations |
| Module | platform |
| Size | M |
| Labels | arch, phase:1, module:platform, type:chore, size:M |
| Depends on | 0002, 0010 |
| Blocks | 0012, 0013, 0014, 0029, 0030, 0035, 0039, 0064 |
| Repos | mulearnbackend |

## Why

No workflow runs tests today: `.github/workflows/` only deploys. Every later issue relies on CI to catch mistakes ([12-testing-and-quality-gates.md](../12-testing-and-quality-gates.md#ci-pipelines)).

## Before you start

- Issues 0002 (safe runner) and 0010 (ruff) must be merged.
- Look at the existing workflows in `.github/workflows/` so names don't clash.

## What to do

1. Create `.github/workflows/ci.yml`, triggered on `pull_request` and on `push` to `dev`, with one job, `unit`:
   1. check out the code and set up Python 3.10;
   2. install `default-libmysqlclient-dev` and `pkg-config` (for `mysqlclient`), then `requirements.txt` and `requirements-dev.txt`;
   3. run `ruff check` and `ruff format --check` (new-code paths only);
   4. run `scripts/test.sh tests/`.
2. Cache pip downloads.
3. Name the job's check `ci / unit` so branch rules can require it (issue 0029).

## Acceptance criteria

- [ ] The workflow runs on this pull request and passes.
- [ ] A deliberately failing test in `tests/` makes the job fail, shown on a throwaway branch and then reverted.
- [ ] The job uses no secrets.

## How to test

The workflow itself is the test. Locally, the same command is:

```sh
scripts/test.sh tests/
```

## Out of scope

- The legacy suite (issue 0013).
- The MySQL tier (issue 0012).
- Building images (issue 0036).

## Notes for reviewers

Check that the workflow can't reach any real database and needs no secrets.
