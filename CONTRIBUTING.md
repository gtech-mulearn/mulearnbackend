# Contributing to the μLearn backend

> **Security problems are never reported in a public issue or pull request.** See [SECURITY.md](SECURITY.md).

## Start here

- [DEVELOPMENT.md](DEVELOPMENT.md): set up a clone, run the tests, and run the whole backend locally.
- [docs/architecture/README.md](docs/architecture/README.md): the architecture this work follows.
- [docs/architecture/github-issues/README.md](docs/architecture/github-issues/README.md): the issues anyone can pick up, with their dependency graphs.

## Picking and claiming an issue

1. **Find an open issue whose dependencies have all merged.** Its header table lists "Depends on", and the project board shows ready issues as "Ready".
2. **Read its "Before you start".** It links everything you need; nothing else is assumed.
3. **Comment on the issue to claim it,** so two people don't do the same work. If you stop, say so, so someone else can pick it up.
4. **New here?** Start with an issue labelled `good first issue`.

`maintainer-only` issues need production access, production data or a private repository. They're listed so the whole plan is visible, but only maintainers take them.

## Branches and pull requests

- **One branch and one pull request per issue,** from `dev` and into `dev`, unless the maintainers name an integration branch for a batch of work. Name the branch `<type>/<issue id>-<short-name>`, for example `chore/0005-report-missing-settings`.
- **Do exactly what the issue says.** Anything listed under "Out of scope" goes in its own issue.
- **Fill in the pull request template:**
  - the issue (`Closes #N`) and what changed;
  - the tests you ran, with their output;
  - any schema change;
  - the acceptance criteria you checked.
- **Write commit messages in the history's style:** `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `ci:`, with an optional scope, for example `chore(settings): …`.
- **CI must pass.** On every pull request, the `ci / unit` check runs ruff, the import contracts and the unit test tier, `ci / legacy` runs the whole legacy suite and fails on any failure that isn't in `tests/legacy_baseline.txt`, and `ci / mysql` runs the MySQL tier on MySQL 8.0 and 8.4. Which tier a test belongs to is in [tests/README.md](tests/README.md).

## Review rules

- **A maintainer reviews every pull request.**
- **Issues labelled `core-review` need two approvals, one of them from a maintainer.** These touch money, roles, auth, the ledger, the outbox or deploys.
- **The branch rules** (`.github/rulesets/`, applied with `scripts/apply_rulesets.sh`) protect `dev`, `staging` and `production`:
  - changes arrive only through a pull request, with at least 1 approval;
  - an approval is dismissed when new commits are pushed;
  - code owners (`.github/CODEOWNERS`) must approve changes to the paths they own, `.github/workflows/` included;
  - the `unit`, `legacy`, `mysql (8.0)`, `mysql (8.4)` and `two reviewers` checks must pass;
  - no force pushes and no deletions.
- **The `two reviewers` check** (`.github/workflows/two-reviewers.yml`) fails a pull request into those branches that touches a core-review path with fewer than 2 approvals. The paths are `building_blocks/authz/`, `building_blocks/messaging/`, `modules/contributions/`, `modules/identity_access/`, `scripts/deploy.sh` and `.github/workflows/`. It re-runs when a review is submitted or dismissed. Only approvals from people with access to the repository count, never bots or outside accounts.
- **Nobody bypasses the rules, maintainers included.** An urgent fix is a pull request like any other: open it, get the approvals and merge it as soon as the checks pass.
- **Schema changes are never made in this repository.** An issue labelled `needs-db-change` needs an alter that a maintainer writes and applies in `db-scripts` first. `schema/latest.sql` is a read-only copy.

## Labels

| Label | Meaning |
|---|---|
| `arch` | Part of the architecture programme |
| `phase:N` | The phase it belongs to |
| `module:<name>` | The module, `building_blocks`, or `platform` for repo-wide plumbing |
| `type:feature` / `type:chore` / `type:docs` / `type:epic` | The kind of work |
| `size:S` / `size:M` / `size:L` | About ½ day, 1 day or 2 days for someone new to the repo |
| `good first issue` | Small, with no dependencies, no schema change and no money, auth or ledger code |
| `needs-db-change` | Needs a schema change, which a maintainer writes and applies in `db-scripts` first |
| `core-review` | Money, roles, auth, the ledger, the outbox or deploys: two approvals, one from a maintainer |
| `maintainer-only` | Needs production access, production data or a private repository |
| `repo:<name>` | The work happens in another repository |
| `status:blocked` | A dependency hasn't merged yet |

## Code style

- **ruff checks and formats new code** (`building_blocks/`, `modules/`, `tests/` and `scripts/`; see `ruff.toml`). Run `ruff check --fix` and `ruff format`, or install the hook once with `pre-commit install`.
- **Legacy packages aren't reformatted.** Leave their style alone in unrelated changes.
- **Django deprecation warnings are errors in new code** (`building_blocks/`, `modules/`, `tests/`). Use the replacement Django names instead. Legacy code only warns, and CI's `legacy` job reports how many warnings remain.
- **Import contracts** keep `building_blocks` free of business and legacy code ([04-module-rules.md](docs/architecture/04-module-rules.md)). Run `lint-imports` to check them. `.importlinter` is generated: change `tests/architecture/module_graph.toml`, run `python scripts/gen_importlinter.py`, and commit both.
