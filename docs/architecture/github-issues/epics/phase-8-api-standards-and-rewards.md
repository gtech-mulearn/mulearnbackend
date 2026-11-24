# Phase 8: API standards and rewards

| | |
|---|---|
| Epic | phase-8-api-standards-and-rewards |
| Phase / milestone | Phase 8: API standards and rewards |
| Labels | arch, phase:8, type:epic |

## What it will contain

From [07-api-standards.md](../../07-api-standards.md) and [ADR-044](../../adr/ADR-044-api-standards-v1-2.md):

- **The generated OpenAPI spec in CI,** with the `oasdiff` gate: report-only first, then blocking.
- **App versions:** `X-App-Version` recorded, then the minimum-version flag (`426 platform.upgrade_required`).
- **Page caps:** `perPage` capped at 200 behind a flag, then 100, after the dashboard and app callers are checked.
- **Exports and reports** become `bulk` jobs with signed URLs, so no CSV is built on a request thread.
- **`Deprecation` and `Sunset` headers** on anything being retired.
- **Dashboard polling** at 120 s while visible, with ETag and 304 responses.
- **The `rewards` module:**
  - vouchers, with unguessable codes and a single-use redemption that publishes `VoucherRedeemed`;
  - coupons and referrals;
  - the coin tables stay frozen ([ADR-054](../../adr/ADR-054-mucoin-external-consumer.md)).

## Entry conditions

- Issue 0019 (envelope and exception handler) is in production.
- The `contributions` cut-over is finished, so voucher awards can go through events.

## Exit criteria

- `oasdiff` blocks pull requests.
- `X-App-Version` is present on at least 90% of app traffic within six weeks of the app release.
- No CSV is built on the web role.
- A voucher can be redeemed only once, even under concurrent redemption, and its award is keyed `voucher:<id>`.
