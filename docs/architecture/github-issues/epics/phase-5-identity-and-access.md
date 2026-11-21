# Phase 5: identity and access

| | |
|---|---|
| Epic | phase-5-identity-and-access |
| Phase / milestone | Phase 5: Identity and access |
| Labels | arch, phase:5, module:identity_access, type:epic |

## What it will contain

From [08-auth-and-permissions.md](../../08-auth-and-permissions.md) and [ADR-007](../../adr/ADR-007-scoped-grants-and-policies.md), [ADR-036](../../adr/ADR-036-rate-limiting.md) and [ADR-046](../../adr/ADR-046-tokens-keys-service-clients.md):

- **The `identity_access` module.** It owns `role` and `user_role_link` as scoped grants, with the commands `request_role`, `verify_grant`, `revoke_grant` and `grant_directly`, plus `GrantChanged` and cache invalidation. The 24 functions that write `user_role_link` today move onto these commands.
- **The role catalogue,** with every role classified as privileged or not.
- **Default deny:**
  1. mark every existing public view explicitly (a behaviour-preserving codemod);
  2. switch `DEFAULT_PERMISSION_CLASSES` to authenticated;
  3. add the auth-coverage ratchet.
- **Policies replace role-name checks** module by module, with shadow-mode reports before enforcement.
- **The generated authorization test matrix** and the union-of-grants property test.
- **Rate-limit keys** per identifier and device; campus event mode; Turnstile on web signup and OTP.
- **Key separation, phase 1:** a key per signing purpose with a `kid`, upload tickets for the media worker, and `SECRET_KEY` rotation through fallbacks.
- **Per-service MySQL users** with grants generated from the ownership list.

## Entry conditions

- Issue 0027 (authorization core) and issue 0090 (service clients) have merged.
- The Phase 0 security epic is closed.
- Phase 4's switch work is not mid-flight: only one core domain switches at a time.

## Exit criteria

- No routed view is implicitly public.
- Shadow disagreement is under 0.1% over 7 days, with every case explained, before each enforcement flip.
- The 401/403 rate per path stays within 5% of baseline after each flip.
- The refresh success rate is unchanged across the key change.
- Services that only check a caller hold ticket keys, never token signing keys.
