# `contributions`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

Record submissions of work from every channel (dashboard, app, Discord, partners). It handles peer approval and appraisal. It is the only place that awards, reverses, penalises or adjusts karma, through an append-only ledger with `wallet.karma` as its projection. It also runs reconciliation ([ADR-004](../adr/ADR-004-karma-ledger.md), [ADR-018](../adr/ADR-018-channel-agnostic-contributions.md)).

## Kind

**Core.** Karma correctness is the product.

## Tables it owns

- `karma_activity_log`: submissions. It gains `source`, `source_ref`, `status` and `award_generation` (issue 0080).
- `karma_ledger_entry`: new, append-only ([06-data-and-schema.md](../06-data-and-schema.md#the-karma-ledger)).
- `wallet`: **the karma column only.** `wallet.coin` is frozen ([ADR-054](../adr/ADR-054-mucoin-external-consumer.md)).

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `karma_activity_log` | `api/dashboard/lc/dash_lc_serializer.py` :: `create`<br>`api/dashboard/lc/dash_lc_view.py` :: `post`<br>`api/dashboard/manage_interns/reviews/review_views.py` :: `_award_missing_milestone_karma`<br>`api/dashboard/manage_interns/reviews/review_views.py` :: `patch`<br>`api/dashboard/manage_interns/tasks/serializers.py` :: `update`<br>`api/dashboard/manage_interns/tasks/tasks_views.py` :: `post`<br>`api/dashboard/profile/profile_serializer.py` :: `create_karma_activity_log`<br>`utils/karma.py` :: `add_karma`<br>`utils/karma.py` :: `remove_karma` | Discord bot |
| `wallet` (karma column; coin column frozen, ADR-054) | `api/dashboard/lc/dash_lc_serializer.py` :: `create`<br>`api/dashboard/lc/dash_lc_view.py` :: `post`<br>`api/dashboard/manage_interns/reviews/review_views.py` :: `_award_missing_milestone_karma`<br>`api/dashboard/manage_interns/reviews/review_views.py` :: `patch`<br>`api/dashboard/manage_interns/tasks/serializers.py` :: `update`<br>`api/dashboard/manage_interns/tasks/tasks_views.py` :: `post`<br>`api/dashboard/profile/profile_serializer.py` :: `create_karma_activity_log`<br>`api/dashboard/referral/referral_view.py` :: `post` (the `coin` column only, frozen)<br>`api/register/serializers.py` :: `create`<br>`utils/karma.py` :: `add_karma`<br>`utils/karma.py` :: `remove_karma` | Discord bot |

## Invariants

- **One submission per source reference.** Only an appraiser decides, and nobody approves their own submission.
- **A replayed reaction or retried request changes nothing:** the state machine plus `UNIQUE(source, source_ref)`.
- **The balance equals the sum of ledger entries.** Only `penalty` entries may take it below zero; a negative `adjustment` stops at zero.
- **Entries are never edited or deleted.** Removing a submission writes a reversal.
- **Lock order:** submission row, then wallet row, then ledger rows, in every command.

## Public API (public.py)

| Commands | Queries |
|---|---|
| `record_submission(principal, task, source, source_ref, proof)` | `get_balance(user_id)` |
| `peer_approve(principal, submission_id)` | `ledger_balance(user_id)` |
| `appraise(principal, submission_id, expected_generation)` | `list_entries(user_id, cursor, limit)` |
| `reverse_award(principal, entry_id, reason)` | `appraisal_queue(principal, cursor, limit)` |
| `penalize(principal, user_id, amount, reason)` | `submission_status(submission_id)` |
| `adjust(principal, user_id, amount, reason)` | `task_id_for_hashtag(hashtag)` |
| `award_direct(source, source_ref, user_id, amount)` (system sources) | |

DTOs and events are defined in `contracts.py`.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `contributions.submission_recorded`, `submission_approved`, `submission_rejected` | `rewards.voucher_redeemed` → `award_direct(voucher:<id>)` |
| `contributions.karma_awarded`, `karma_reversed`, `karma_penalized`, `karma_adjusted` | `communities.learning_circle_meeting_reported` → `award_direct(lc:<kind>:<id>)` |
| `task.verified` (integration event for `mucoin-service`, [ADR-054](../adr/ADR-054-mucoin-external-consumer.md)) | `interns.intern_work_approved` → `award_direct(intern:<ref>)` |
| | `people.social_link_verified` → `award_direct(social:<link_id>)` |

## Allowed dependencies

`identity_access.public` (authorization), `people.public` (attribution: home path, campus), `learning.public` (task snapshot, once it exists), `building_blocks`.

## What moves from legacy code

- `utils/karma.py` `add_karma` and `remove_karma`
- the karma writes in `api/dashboard/lc/`, `api/dashboard/manage_interns/`, `api/dashboard/profile/profile_serializer.py` and `api/register/serializers.py`
- `api/dashboard/discord_moderator/`
- the Discord bot's karma and wallet SQL, which moves to the internal API (issues 0091, 0103 and the cut-over epic)

## Cut-over steps

1. [0080](../github-issues/0080-ledger-alter.md): Add the karma ledger table and the submission columns (Phase 4)
1. [0081](../github-issues/0081-contributions-module-and-models.md): Create the contributions module and its models (Phase 4)
1. [0082](../github-issues/0082-submission-state-machine.md): Add the submission state machine and ledger key rules (Phase 4)
1. [0083](../github-issues/0083-ledger-property-tests.md): Add property tests for the ledger rules (Phase 4)
1. [0084](../github-issues/0084-record-and-peer-approve.md): Add the record_submission and peer_approve commands (Phase 4)
1. [0085](../github-issues/0085-appraise-and-reverse.md): Add the appraise and reverse_award commands (Phase 4)
1. [0086](../github-issues/0086-penalize-and-adjust.md): Add the penalize and adjust commands (Phase 4)
1. [0087](../github-issues/0087-contributions-selectors.md): Add balance, entry and appraisal-queue selectors (Phase 4)
1. [0088](../github-issues/0088-ledger-concurrency-tests.md): Add MySQL concurrency tests for awards (Phase 4)
1. [0091](../github-issues/0091-internal-contributions-api.md): Add the internal contributions API for the Discord bot (Phase 4)
1. [0093](../github-issues/0093-classify-karma-log.md): Add a command that classifies existing karma rows (Phase 4)
1. [0094](../github-issues/0094-opening-balances-and-backfill.md): Add opening balances and the award backfill (Phase 4)
1. [0095](../github-issues/0095-ledger-writes-flag-and-utils-karma.md): Route utils/karma.py through contributions behind a flag (Phase 4)
1. [0096](../github-issues/0096-move-learning-circle-karma-writes.md): Move learning-circle karma writes onto contributions (Phase 4)
1. [0097](../github-issues/0097-move-intern-karma-writes.md): Move intern karma writes onto contributions (Phase 4)
1. [0098](../github-issues/0098-move-profile-karma-write.md): Move the profile karma write onto contributions (Phase 4)
1. [0099](../github-issues/0099-move-signup-and-referral-wallet-writes.md): Move the signup wallet write onto contributions (Phase 4)
1. [0100](../github-issues/0100-reconciliation-ticket-mode.md): Add nightly karma reconciliation in ticket mode (Phase 4)
1. [0104](../github-issues/0104-rollout-ledger-writes.md): Turn on ledger writes in production (Phase 4)
1. [Epic: Phase 4: finish the contributions cut-over](../github-issues/epics/phase-4-contributions-cutover.md)

## Tests this module needs

- Hypothesis property tests of the ledger rules: generations, reversals, penalties (issue 0083).
- MySQL-tier concurrency tests: double appraisal, replayed reaction, a reversal before its award (issue 0088).
- Characterization tests for every legacy writer before it moves (issues 0095–0099).
- The reconciliation report is empty for backend sources for 14 days before ledger writes go to 100%.

## Open questions

- How existing negative wallets are represented in opening balances (decided before issue 0094 runs on production).
- The Discord submission key: message id + action + actor is the proposal; confirm it before the bot switches.
