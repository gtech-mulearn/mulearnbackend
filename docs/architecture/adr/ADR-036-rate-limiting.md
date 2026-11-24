# ADR-036: Rate limiting and abuse controls

Status: Accepted (amended on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. `REST_FRAMEWORK` sets no project-wide throttle classes.

## Context

At campus events, hundreds of students sign up or submit within minutes from behind one college
NAT or carrier-grade NAT address. Limits keyed only on IP would lock out a whole campus, while
limits that are too loose invite credential and OTP abuse.

## Options considered

- **Edge limits for volume, application limits for semantics, with identifier- and device-keyed
  keys.**
- **GCRA in Redis everywhere now:** smoother, but a fixed-window limiter covers current needs.
- **IP-keyed limits only:** campus lockouts.

## Decision

1. **Where limits run:**
   - at the edge (Cloudflare or nginx), for volumetric and scraper limits;
   - in the application (a fixed-window limiter in `building_blocks`), for semantic limits.
   - GCRA replaces the fixed window behind the same interface only on a trigger.
2. **Keys:**
   - authenticated callers are keyed by user UUID;
   - anonymous authentication flows are keyed by the normalised identifier and a device id;
   - IP serves only as a high ceiling, set above a campus burst (about 3,000 requests per
     10 minutes by default);
   - an audited **campus event mode** raises ceilings for listed campus egress ranges during an
     event.
3. **The real client IP** is derived from a measured, trusted proxy hop count and forwarded to
   the authserver over a trusted hop.
4. **Turnstile** protects web signup and OTP requests. The app relies on device-keyed limits.
5. **When the state store is unavailable:**
   - authentication limiters fall back to a coarse in-process limiter per worker;
   - other limiters fail open.
   - Limiter state lives on the `state` cache alias ([ADR-043](ADR-043-redis-cache-and-state.md)).
6. Existing product rulings on specific limits stay, keyed as described above and covered by
   campus event mode.

## Consequences

- Campus bursts are admitted, while abuse is still bounded per identifier and device.
- Campus event mode needs an owner and an audit trail.

## Revisit when

- Campus lockouts are reported, or a burst that gets past the limits is measured.

## Related ADRs

[ADR-043](ADR-043-redis-cache-and-state.md), [ADR-046](ADR-046-tokens-keys-service-clients.md)
