# ADR-039: Retire Channels and Daphne; realtime through push and conditional polling

Status: Accepted (new on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started. `daphne` is in `INSTALLED_APPS` and `api/routing.py` defines WebSocket routes; no first-party client opens a WebSocket.

## Context

No first-party client (the web dashboard or the mobile app) opens a WebSocket. Keeping an ASGI
stack, Channels and its dependencies only for unused routes adds runtime and dependency cost, and
it keeps the request path more complex than it needs to be. Some signal receivers are registered
only as a side effect of importing the WebSocket routing.

## Options considered

- **Keep Channels as an isolated ASGI role.**
- **Remove it,** and use FCM push plus conditional polling.
- **Server-Sent Events.**

## Decision

1. **Confirm that no WebSocket users remain.** Check the marketing site's code, and edge logs for
   WebSocket upgrades.
2. **Add `GET /api/v1/public/landing-stats/`** with `Cache-Control: public, max-age=60`, and move
   the marketing site to it.
3. **Decide each signal receiver on its own:**
   - delete the receiver that exists only to broadcast landing counts;
   - move the cache invalidators to `AppConfig.ready()`, with a test that they register. They then
     also fire for writes made in workers, which is a deliberate change.
4. **Delete the WebSocket routes and consumers,** and remove `daphne`, `channels`,
   `channels-redis` and Twisted.
5. **Unread counts** use ETag/304 plus a push-triggered refresh. Dashboard polling slows while the
   tab is visible and stops when it is hidden.

## Consequences

- Fewer dependencies, and a pure WSGI serving model ([ADR-006](ADR-006-gunicorn-gthread-behind-nginx.md)).
- If a live-collaboration feature is ever needed, it gets its own ASGI role.

## Revisit when

- A product need for live collaboration arrives. It gets a separate ASGI role with its own pool
  and authentication.

## Related ADRs

[ADR-006](ADR-006-gunicorn-gthread-behind-nginx.md), [ADR-047](ADR-047-notification-pipeline.md)
