# Add the `@command` decorator and its transaction guard

| | |
|---|---|
| ID | 0021 |
| Phase / milestone | Phase 1: Foundations |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:1, module:building_blocks, type:feature, size:M, core-review |
| Depends on | 0014 |
| Blocks | 0059, 0074 |
| Repos | mulearnbackend |

## Why

Every write must be one transaction, owned by one module. A command of one module must never run inside another module's open transaction. The `@command` decorator makes this the default, and detects violations ([ADR-041](../adr/ADR-041-transactions-and-consistency.md)).

## Before you start

- Issue 0014 must be merged.
- Read [Transactions and side effects](../04-module-rules.md#transactions-and-side-effects).

## What to do

1. Create `building_blocks/persistence/__init__.py` and `building_blocks/persistence/command.py` with:
   - `class CrossModuleTransaction(RuntimeError)`, a programming error rather than a `DomainError`;
   - `command(owner: str)`, a decorator for functions and methods (use `functools.wraps`). It keeps the owners of the running commands on a `ContextVar[tuple[str, ...]]` stack. Push on entry and reset with the token in `finally`, so the stack can't leak between requests or after an exception.
2. On entry, the decorator checks for two cases:
   - **Another module's transaction.** The stack isn't empty, and its top differs from `owner`.
   - **A legacy transaction.** The stack is empty, but legacy code has an atomic block open. Ignore the blocks Django opens for test cases, which it marks with `_from_testcase`: the check is `any(not getattr(b, "_from_testcase", False) for b in connection.atomic_blocks)`. A legacy caller is allowed only if its call site is listed in `tests/architecture/allowlists/legacy_tx_callers.toml`. The call site is the nearest stack frame outside `building_blocks/` and `modules/`, written `path/from/repo/root.py::function`.

   Any other case is a violation. When the new setting `COMMAND_GUARD_STRICT` is on, the decorator raises `CrossModuleTransaction`, naming both owners or the call site. When it is off, it logs a warning and adds 1 to a module-level counter that `violation_count()` returns. Issue 0043 exports that counter as a metric.
3. Add `COMMAND_GUARD_STRICT` to the settings, read with `decouple` and defaulting to `DEBUG`. Make `scripts/test.sh` and `scripts/test.ps1` export `COMMAND_GUARD_STRICT=1`, because pytest-django switches `DEBUG` off during tests.
4. The decorator then opens `transaction.atomic()` around the call.
5. **Deadlock retries happen only at the outermost level.** If this call opened the outermost transaction (the stack was empty and no legacy block was open), it retries the whole call when MySQL reports a deadlock (`OperationalError` with `args[0] == 1213`). It makes at most 3 attempts in all, sleeping a random 50–200 ms between them. Take `sleep` as an injectable function, so tests don't wait. A nested call never retries: it re-raises, so the outermost command can retry.
6. Create `tests/architecture/allowlists/legacy_tx_callers.toml` containing `callers = []` and a header comment. The comment says the file lists the legacy call sites allowed to wrap a command, one `path::function` string each, and that it only shrinks. The decorator reads it once per process.
7. Add `building_blocks/tests/test_command.py` on the SQLite tier; no schema table is needed. Use `@pytest.mark.django_db` for most tests, and `transaction=True` for the ones that need no outer transaction. Simulate a deadlock by raising `OperationalError(1213, "Deadlock found")` from the wrapped function. Cover:
   - nested commands with the same owner are fine;
   - a different owner raises when strict, and only counts when not;
   - a command inside a legacy `transaction.atomic()` raises from an unlisted site, and runs from a listed one;
   - a command called outside any transaction opens one (`transaction=True`);
   - a deadlock is retried at the outermost level, 3 attempts in all, then re-raised (`transaction=True`), and isn't retried when nested;
   - the stack is empty after an exception;
   - the decorator works on a method.

## Acceptance criteria

- [ ] All tests pass with `scripts/test.sh building_blocks/tests/`.
- [ ] The decorator works on both functions and methods.
- [ ] A command called outside any transaction opens one.
- [ ] With `COMMAND_GUARD_STRICT` off, a violation logs and counts but doesn't raise.

## How to test

```sh
scripts/test.sh building_blocks/tests/
```

## Out of scope

- Using it in legacy code (as modules move).

## Notes for reviewers

This is core infrastructure for every write. Check that the retry happens only when the command opened the outermost transaction, that the stack can't leak between requests, and that the blocks marked `_from_testcase` are the only ones ignored.
