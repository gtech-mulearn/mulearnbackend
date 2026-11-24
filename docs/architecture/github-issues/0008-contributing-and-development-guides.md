# Add CONTRIBUTING.md and DEVELOPMENT.md

| | |
|---|---|
| ID | 0008 |
| Phase / milestone | Phase 0: Stabilise and secure |
| Module | platform |
| Size | S |
| Labels | arch, phase:0, module:platform, type:docs, size:S |
| Depends on | 0004 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

Contributors need one place that explains how to start, how to pick an issue and how work is reviewed. They also need templates that make pull requests and architecture tasks consistent. Today the repository has a README and two issue templates, but no contributor or development guide.

## Before you start

- Issue 0004 (the local environment) must be merged, because DEVELOPMENT.md describes it.
- Read [16-contributing-to-the-architecture.md](../16-contributing-to-the-architecture.md) and [the issues README](README.md).

## What to do

1. Create `CONTRIBUTING.md`. It covers:
   - how to pick and claim an issue;
   - branches and pull requests;
   - the review rules, including `core-review`;
   - the labels;
   - links to `docs/architecture/README.md` and `docs/architecture/github-issues/README.md`.
2. Create `DEVELOPMENT.md`. It covers:
   - prerequisites;
   - `cp .env.local.example .env.local`;
   - `docker compose -f docker-compose.local.yml up -d`;
   - `scripts/test.sh` and `scripts/test.sh --mysql`;
   - the warning never to run `pytest` against a configured database;
   - troubleshooting for the system-user check and port clashes.
3. Add `.github/pull_request_template.md`, asking for: the issue, what changed, the tests run (pasted output), any schema change, and the acceptance criteria checked.
4. Add `.github/ISSUE_TEMPLATE/architecture_task.md`, mirroring the issue template in `docs/architecture/github-issues/README.md`. Keep the existing `feature.md` and `feature_form.yml`.
5. Create `SECURITY.md`. It says how to report a vulnerability privately (GitHub's private vulnerability reporting for this repository), that vulnerabilities are never filed as public issues or pull requests, and what reply to expect. Link it from CONTRIBUTING.md.

## Acceptance criteria

- [ ] A new contributor can follow DEVELOPMENT.md from a fresh clone to a green `scripts/test.sh`.
- [ ] CONTRIBUTING.md links resolve.
- [ ] The pull-request template appears on new pull requests.
- [ ] `SECURITY.md` exists, and the repository's private vulnerability reporting is switched on.

## How to test

Follow DEVELOPMENT.md on a clean checkout and paste the `scripts/test.sh` output in the pull request.

## Out of scope

- Rewriting the main README.

## Notes for reviewers

Check every command against the files issues 0002 and 0004 actually created.
