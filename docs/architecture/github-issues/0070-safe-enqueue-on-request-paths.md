# Use safe_enqueue on request paths

| | |
|---|---|
| ID | 0070 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | M |
| Labels | arch, phase:3, module:platform, type:chore, size:M |
| Depends on | 0069 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

There are 7 `.delay()` or `.apply_async()` calls in `api/` and `utils/` (outside tests) that run in request code. Each should go through `safe_enqueue`.

## Before you start

- Issue 0069 must be merged.
- List the call sites with `git grep -n ".delay(\|.apply_async(" -- api utils`.

## What to do

1. Replace each call with `safe_enqueue(task, ...)`, keeping the arguments.
2. List every changed call site in the pull request, with what triggers it.
3. Add or adjust one test per call site where a test exists. Otherwise, add a test that the task is enqueued after commit.

## Acceptance criteria

- [ ] `git grep -n ".delay(\|.apply_async(" -- api utils` shows no request-path call outside tests.
- [ ] Both test tiers pass.

## How to test

```sh
scripts/test.sh tests/
```

## Out of scope

- Changing what any task does.

## Notes for reviewers

Check each site's arguments are JSON-serialisable.
