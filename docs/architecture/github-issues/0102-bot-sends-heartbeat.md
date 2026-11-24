# Send heartbeats from the Discord bot

| | |
|---|---|
| ID | 0102 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | integrations |
| Size | S |
| Labels | arch, phase:4, module:integrations, type:feature, size:S, maintainer-only, repo:aaronchettan |
| Depends on | 0101 |
| Blocks | none |
| Repos | aaronchettan |

## Why

The heartbeat endpoint only helps if the bot calls it with real counts.

## Before you start

- Maintainer-only: this work is in the private bot repository.
- Issue 0101 must be merged.
- A service client for the bot exists (`manage.py service_client create`).

## What to do

1. In the bot, count the task-channel events it processed and the channel activity it saw each minute.
2. Every minute, `POST /api/v1/internal/integrations/heartbeat/` with those counts, using its service credentials.
3. Log failures to send, but never block event processing on them.

## Acceptance criteria

- [ ] Heartbeats arrive every minute on staging.
- [ ] Stopping event processing in a drill triggers the alert within 10 minutes.

## How to test

Run a drill on staging and record the alert time.

## Out of scope

- Moving the bot's karma writes (issue 0103 and the cut-over epic).

## Notes for reviewers

The counts must come from processed events, not a timer.
