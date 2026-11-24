# `rewards`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

Vouchers, coupons and referral rewards. It never moves karma itself: a redeemed voucher publishes an event that `contributions` turns into an award. **Coins are not part of this module:** the coin economy lives in `mucoin-service` ([ADR-054](../adr/ADR-054-mucoin-external-consumer.md)).

## Kind

Supporting.

## Tables it owns

- `voucher_log`, `user_coupon_link`, `user_referral_link`
- **frozen** (no new reads or writes): `mucoin_activity_log`, `mucoin_invite_log`, the referral coin debit and `wallet.coin`

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `mucoin_activity_log` (frozen, ADR-054) | `api/dashboard/referral/referral_view.py` :: `post` | — |
| `mucoin_invite_log` (frozen, ADR-054) | `api/dashboard/referral/referral_view.py` :: `post` | — |
| `user_coupon_link` | none | Discord bot |
| `user_referral_link` | `api/register/serializers.py` :: `create` | — |
| `voucher_log` | `api/dashboard/karma_voucher/karma_voucher_serializer.py` :: `create`<br>`api/dashboard/karma_voucher/karma_voucher_serializer.py` :: `update`<br>`api/dashboard/karma_voucher/karma_voucher_view.py` :: `patch`<br>`api/dashboard/karma_voucher/karma_voucher_view.py` :: `post` | Discord bot |

## Invariants

- Voucher codes are unguessable.
- A voucher is redeemable once, through a conditional `UPDATE … WHERE status = 'issued'`.
- A redemption produces exactly one award, keyed `voucher:<id>`.

## Public API (public.py)

`issue_vouchers(batch)` (a bulk job), `redeem_voucher(principal, code)`, `consume_coupon(...)`, `record_referral(...)` (consumer); `vouchers_for(user_id, cursor)`, `referrals_of(user_id)`.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `rewards.voucher_issued`, `voucher_redeemed`, `coupon_consumed` | `people.user_registered` (referral attribution) |

## Allowed dependencies

`people.public`, `identity_access.public`.

## What moves from legacy code

- `api/dashboard/karma_voucher/` and `utils/karma_voucher.py`
- `api/dashboard/referral/` (its only wallet write is the frozen coin debit, which stays on the legacy path; issue 0099 stops it overwriting `wallet.karma`)
- `api/dashboard/coupon/`

## Cut-over steps

1. [0099](../github-issues/0099-move-signup-and-referral-wallet-writes.md): Move the signup wallet write onto contributions (Phase 4)
1. [Epic: Phase 8: API standards and rewards](../github-issues/epics/phase-8-api-standards-and-rewards.md)

## Tests this module needs

- Concurrent redemption of one voucher produces one award.
- A replayed `VoucherRedeemed` produces no second award.

## Open questions

- Whether the frozen coin tables are archived, and when (a later decision; [ADR-054](../adr/ADR-054-mucoin-external-consumer.md)).
