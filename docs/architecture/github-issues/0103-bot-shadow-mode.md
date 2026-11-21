# Run the bot's karma path through the internal API in shadow mode

| | |
|---|---|
| ID | 0103 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | integrations |
| Size | L |
| Labels | arch, phase:4, module:integrations, type:feature, size:L, maintainer-only, repo:aaronchettan |
| Depends on | 0091, epic:phase-0-security-hardening |
| Blocks | none |
| Repos | aaronchettan |

## Why

Before the bot stops writing karma itself, every action is also sent to the internal API in dry-run mode, and the two results are compared. Any difference is a rule the bot and the backend disagree on, and it must be explained before switching.

## Before you start

- Maintainer-only: this work is in the private bot repository.
- Issue 0091 must be merged.
- The Phase 0 security epic must be closed.

## What to do

1. For each karma-affecting action (submit, peer approval, appraisal, reversal, penalty), after the bot's own write, call the matching internal endpoint with `X-Dry-Run: true` and the same inputs.
2. Compare the API's would-be result with what the bot wrote: the award amount, the status and the generation. Log any difference with the message id.
3. Post a daily summary of differences to the maintainers' channel.
4. Put this behind a bot setting, so it can be turned off instantly.

## Acceptance criteria

- [ ] Shadow calls run for 7 days on production with no effect on behaviour.
- [ ] Every difference is either explained or fixed, and the explanations are recorded on the issue.

## How to test

Record the daily summaries on the issue.

## Out of scope

- Switching any command to the API (the cut-over epic).

## Notes for reviewers

Make sure dry-run calls can't persist anything (issue 0091 covers this), and that the bot's own behaviour is unchanged.
