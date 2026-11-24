# Make the grit meter fail closed and run once per user per day

| | |
|---|---|
| ID | 0079 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | gamification |
| Size | M |
| Labels | arch, phase:3, module:gamification, type:chore, size:M, repo:scheduler-service |
| Depends on | none |
| Blocks | none |
| Repos | scheduler-service |

## Why

The grit meter in `scheduler-service` (the public `gtech-mulearn/scheduler-service` repository) lowers levels for inactive learners. When it can't read its on/off switch, it runs anyway, and it isn't safe to run twice for the same user on the same day. Until `gamification` absorbs it, it must fail closed and be idempotent.

## Before you start

- This work is in the `scheduler-service` repository. Read its grit-meter service (`grit-meter.service.ts`) and how it reads its kill switch.
- `user_lvl_link` has a `last_level_down_at` column.

## What to do

1. If reading the kill switch fails for any reason, skip the run and log an error. Never default to "on".
2. Before lowering a learner's level, skip them if `last_level_down_at` is already on the same IST day.
3. Do each learner's update, and its log row, in one transaction.
4. Send any email only after the transaction commits, and log failed sends.
5. Add tests in that repository for each rule.

## Acceptance criteria

- [ ] A failure to read the switch results in no changes.
- [ ] Running the job twice on one IST day lowers each learner at most once.
- [ ] No email is sent for a rolled-back update.

## How to test

Run the repository's test suite and paste the output in the pull request there.

## Out of scope

- Moving the grit meter into the backend (Phase 6).

## Notes for reviewers

Open the pull request in `scheduler-service` and link it from the backend issue.
