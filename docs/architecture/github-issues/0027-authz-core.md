# Add principals, grants and the policy registry

| | |
|---|---|
| ID | 0027 |
| Phase / milestone | Phase 1: Foundations |
| Module | building_blocks |
| Size | L |
| Labels | arch, phase:1, module:building_blocks, type:feature, size:L, core-review |
| Depends on | 0014, 0017, 0026 |
| Blocks | 0084, 0087, 0090 |
| Repos | mulearnbackend |

## Why

Users hold several roles at once, each verified separately, and some scoped to an interest group. Authorization must be the union of what each verified grant allows, never a combination ([ADR-007](../adr/ADR-007-scoped-grants-and-policies.md), [08-auth-and-permissions.md](../08-auth-and-permissions.md)).

## Before you start

- Issues 0014, 0017 and 0026 must be merged.
- Read `db/user.py` `UserRoleLink` (it has `verified`, `ig`, `is_active` and `revoked_at`).

## What to do

1. Create `building_blocks/authz/core.py` with:
   - frozen dataclasses `Grant(role: str, scope_type: str, scope_id: str, status: str)` and `Principal(user_id: str | None, grants: tuple[Grant, ...], client_id: str | None = None)`;
   - `GLOBAL_SCOPE = "global"`;
   - `policy(action: str)`, a decorator registering `fn(grant, resource) -> bool`, one grant at a time;
   - `require(principal, action, resource=None) -> None`, which raises `Forbidden` with code `identity_access.forbidden` unless **any single** verified grant's policy allows it;
   - `principal_of(request) -> Principal`. It loads the caller's active, verified, unrevoked `user_role_link` rows: scope `ig` with the interest-group id when `ig` is set, otherwise `global`. It is memoised per request.
2. Set `request.principal` in `MuLearnAPIView.initial()`.
3. Add a hypothesis property test: for random grant sets and random policies, `require` allows exactly when at least one grant allows alone.
4. Add unit tests for unverified, revoked and inactive links (never authorize) and for interest-group scoping.

## Acceptance criteria

- [ ] All tests pass, including the property test with at least 10,000 examples.
- [ ] Unverified, inactive and revoked role links never authorize anything.
- [ ] No legacy permission check changes.

## How to test

```sh
scripts/test.sh building_blocks/tests/
```

## Out of scope

- Moving role-link writes into `identity_access` (Phase 5).
- Grant caching across requests (Phase 5).

## Notes for reviewers

This decides who may do what. Two reviewers; check the union rule and the verified-only filter carefully.
