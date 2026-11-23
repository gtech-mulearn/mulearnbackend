"""@command(owner): one module's write, in its own transaction (issue 0021, ADR-041).

    @command("events")
    def cancel_event(*, event_id: str) -> None: ...

- **One transaction per write.** The decorated function runs inside transaction.atomic().
- **Plain functions only.** An async or generator function would return before its body runs,
  outside the transaction, so decorating one raises TypeError.
- **No module runs inside another module's transaction.** The owners of the running commands
  are kept on a ContextVar stack, each only while its command's body runs. So a callback
  registered with transaction.on_commit(), which Django runs after the commit, starts with an
  empty stack and may run any module's command. A command whose owner differs from the one
  already running is a violation. So is a command inside a transaction that legacy code opened,
  unless that call site is listed in tests/architecture/allowlists/legacy_tx_callers.toml.
  Django's own test-case transactions (marked _from_testcase) aren't legacy ones.
- **Violations.** With COMMAND_GUARD_STRICT on, a violation raises CrossModuleTransaction.
  Otherwise it logs a warning and adds 1 to violation_count(), and the command still runs.
- **Deadlocks** (MySQL error 1213) are retried only by a command that opened the transaction
  itself, with no block of any kind already open, at most 3 attempts in all, 50 to 200 ms apart.
  A command inside another block re-raises, because a deadlock has already rolled back the
  enclosing transaction. A deadlock raised by an on_commit callback is never retried: the body
  has committed by then.
- **A retry runs the body again from the start.** The rolled-back attempt's database writes and
  on_commit callbacks are gone, but nothing else is undone. So a command takes ids and reads its
  rows inside the body (or updates with F()), and does anything outside the database (cache,
  Redis, .delay()) through transaction.on_commit().
"""

import functools
import inspect
import logging
import random
import sys
import threading
import time
from contextvars import ContextVar
from pathlib import Path

from django.conf import settings
from django.db import OperationalError, connection, transaction

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

logger = logging.getLogger("building_blocks.persistence")

ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST = ROOT / "tests" / "architecture" / "allowlists" / "legacy_tx_callers.toml"
NEW_CODE = (ROOT / "building_blocks", ROOT / "modules")
MAX_ATTEMPTS = 3
DEADLOCK = 1213

_owners: ContextVar[tuple[str, ...]] = ContextVar("command_owners", default=())
_violations = 0
_violations_lock = threading.Lock()


class CrossModuleTransaction(RuntimeError):
    """A command ran inside another module's transaction: a programming error, not a DomainError."""


def current_owners() -> tuple[str, ...]:
    """The owners of the commands running now, outermost first."""
    return _owners.get()


def violation_count() -> int:
    """How many violations were logged instead of raised in this process (exported by issue 0043)."""
    return _violations


@functools.lru_cache(maxsize=1)
def legacy_callers() -> frozenset[str]:
    """The legacy call sites allowed to wrap a command. Read once per process."""
    with ALLOWLIST.open("rb") as file:
        return frozenset(tomllib.load(file).get("callers", []))


def _legacy_block_open() -> bool:
    return any(not getattr(block, "_from_testcase", False) for block in connection.atomic_blocks)


@functools.lru_cache(maxsize=2048)
def _shown_path(filename: str) -> str | None:
    """A frame's file as shown in the allowlist, or None for building_blocks/ and modules/."""
    path = Path(filename).resolve()
    if any(path.is_relative_to(directory) for directory in NEW_CODE):
        return None
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()


def _call_site() -> str:
    """The nearest caller outside building_blocks/ and modules/, as path/from/repo/root.py::function.

    Walks the frames directly: inspect.stack() reads source lines for every frame, which costs
    milliseconds on each command call inside a legacy transaction.
    """
    frame = sys._getframe(2)  # skip _call_site() and the command's wrapper
    while frame is not None:
        shown = _shown_path(frame.f_code.co_filename)
        if shown is not None:
            return f"{shown}::{frame.f_code.co_name}"
        frame = frame.f_back
    return "<unknown>::<unknown>"


def _violation(message: str) -> None:
    global _violations
    if getattr(settings, "COMMAND_GUARD_STRICT", False):
        raise CrossModuleTransaction(message)
    with _violations_lock:
        _violations += 1
    logger.warning("command guard: %s", message)


def _is_deadlock(error: OperationalError) -> bool:
    return bool(error.args) and error.args[0] == DEADLOCK


def command(owner: str, *, sleep=time.sleep):
    """Run the decorated function or method as ``owner``'s write, in its own transaction."""

    def decorate(function):
        if inspect.iscoroutinefunction(function) or inspect.isasyncgenfunction(function):
            raise TypeError(f"@command can't wrap the async function {function.__qualname__}")
        if inspect.isgeneratorfunction(function):
            raise TypeError(f"@command can't wrap the generator function {function.__qualname__}")

        @functools.wraps(function)
        def run(*args, **kwargs):
            running = _owners.get()
            legacy_open = not running and _legacy_block_open()
            if running and running[-1] != owner:
                _violation(f"a {owner!r} command ran inside a {running[-1]!r} command's transaction.")
            elif legacy_open:
                site = _call_site()
                if site not in legacy_callers():
                    _violation(
                        f"a {owner!r} command ran inside a transaction that legacy code opened at {site}. "
                        f"List the call site in {ALLOWLIST.relative_to(ROOT).as_posix()} only while it moves."
                    )
            # Retry only when this command opens the transaction: inside any open block, a test
            # case's included, a deadlock has already rolled the enclosing transaction back.
            outermost = not running and not connection.in_atomic_block
            attempts = MAX_ATTEMPTS if outermost else 1
            for attempt in range(1, attempts + 1):
                committed = []
                try:
                    with transaction.atomic():
                        if outermost:
                            # Runs first among the on_commit callbacks, so a later callback's
                            # error is known to come after the commit.
                            transaction.on_commit(functools.partial(committed.append, True))
                        # The owner is on the stack only while the body runs. It is reset before
                        # atomic() exits, because Django runs on_commit callbacks during that exit,
                        # after the commit: a callback may run another module's command.
                        token = _owners.set((*running, owner))
                        try:
                            return function(*args, **kwargs)
                        finally:
                            _owners.reset(token)
                except OperationalError as error:
                    if committed or not _is_deadlock(error) or attempt == attempts:
                        raise
                    sleep(random.uniform(0.05, 0.2))

        return run

    return decorate
