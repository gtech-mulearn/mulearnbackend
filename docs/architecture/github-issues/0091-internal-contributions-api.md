# Add the internal contributions API for the Discord bot

| | |
|---|---|
| ID | 0091 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | L |
| Labels | arch, phase:4, module:contributions, type:feature, size:L, core-review |
| Depends on | 0085, 0086, 0090 |
| Blocks | 0103 |
| Repos | mulearnbackend |

## Why

The Discord bot writes karma by raw SQL today. It moves to these internal endpoints one command at a time, so the bot's karma rules end up in one place ([ADR-018](../adr/ADR-018-channel-agnostic-contributions.md), [13-migration-strategy.md](../13-migration-strategy.md#outside-services)).

## Before you start

- Issues 0085, 0086 and 0090 must be merged.

## What to do

1. In `modules/contributions/api/internal_urls.py`, add these `InternalAPIView`s with `required_scope = "contributions.write"`, acting as the member through `X-Act-As-Discord-Id`:
   - `POST /api/v1/internal/contributions/submissions/`: `{hashtag, discordMessageId, proof}` → `record_submission` with `source="discord"` and `source_ref="discord:<message_id>"`;
   - `POST /api/v1/internal/contributions/submissions/<id>/peer-approve/`;
   - `POST /api/v1/internal/contributions/submissions/<id>/appraise/`: `{decision, expectedGeneration}`;
   - `POST /api/v1/internal/contributions/entries/<id>/reverse/`: `{reason}`;
   - `POST /api/v1/internal/contributions/penalties/`: `{discordUserId, amount, reason, discordMessageId}`;
   - `GET /api/v1/internal/contributions/tasks/by-hashtag/<hashtag>/`.
2. **Dry run:** with the header `X-Dry-Run: true`, a command runs inside a transaction that is always rolled back, and returns what it would have done. Shadow mode uses this.
3. All commands are idempotent through their source keys, so the bot can retry safely.
4. Document every request and response, with examples, in `docs/architecture/modules/contributions.md`.
5. Add API tests for each route, including dry-run (nothing persists, no outbox row) and idempotent retries.

## Acceptance criteria

- [ ] Every route works with a service client and the `discord_member` capability, and fails without it.
- [ ] Dry-run calls leave no rows and no events.
- [ ] Retrying any call has no further effect.

## How to test

```sh
scripts/test.sh --mysql modules/contributions/tests/api/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Bot changes (issue 0103).

## Notes for reviewers

Check that the dry-run rollback also covers outbox rows and any wallet update.
