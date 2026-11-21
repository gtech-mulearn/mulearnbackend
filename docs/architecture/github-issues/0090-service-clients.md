# Add service clients and InternalAPIView

| | |
|---|---|
| ID | 0090 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | building_blocks |
| Size | L |
| Labels | arch, phase:4, module:building_blocks, type:feature, size:L, core-review, needs-db-change |
| Depends on | 0012, 0026, 0027, 0071, 0089 |
| Blocks | 0091, 0101 |
| Repos | mulearnbackend |

## Why

The Discord bot must call the backend as itself, with only the scopes it needs, and act for a member only through an explicit, audited capability ([ADR-046](../adr/ADR-046-tokens-keys-service-clients.md)).

## Before you start

- Issues 0026, 0027 and 0089 (applied) must be merged.
- Issues 0012 and 0071 must also be merged.

## What to do

1. Add a `managed = False` model `ServiceClient` in `building_blocks/auth/models.py`.
2. Create `building_blocks/auth/service_clients.py`:
   - secrets are hashed with Django's `pbkdf2_sha256` hasher;
   - `authenticate(client_name, secret)` also accepts the previous secret until `previous_valid_until`;
   - a per-minute quota is counted on the `state` cache.
3. Create `building_blocks/management/commands/service_client.py` (`create`, `rotate`, `disable`). It prints a new secret once and never stores it in plain text. It logs each change with the operator and the reason.
4. Add `InternalAPIView` in `building_blocks/api/views.py`:
   - it authenticates with the header `Authorization: Service <name>:<secret>`;
   - it requires a class attribute `required_scope`;
   - with the `discord_member` capability, it accepts `X-Act-As-Discord-Id` and builds the acting member's `Principal`, stamped with the client's id. Without the capability, the header is refused.
5. Mount `modules/internal_urls.py` at `/api/v1/internal/`.
6. Add tests:
   - wrong secret: 401;
   - missing scope: 403;
   - quota exceeded: 429;
   - `act_as` without the capability: 403;
   - an old secret still works during rotation.

## Acceptance criteria

- [ ] All tests pass.
- [ ] Secrets never appear in logs or the database in plain text.
- [ ] An internal route is unreachable without service credentials.

## How to test

```sh
scripts/test.sh --mysql building_blocks/tests/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Partner OIDC client credentials (later).

## Notes for reviewers

This is authentication. Two reviewers; check the constant-time comparison inside the hasher and the `act_as` refusal path.
