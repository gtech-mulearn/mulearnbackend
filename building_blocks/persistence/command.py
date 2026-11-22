"""@command(owner): one module's write, in its own transaction (issue 0021, ADR-041).

    @command("events")
    def cancel_event(*, event_id: str) -> None: ...

- **One transaction per write.** The decorated function runs inside transaction.atomic().
- **No module runs inside another module's transaction.** The owners of the running commands
  are kept on a ContextVar stack. A command whose owner differs from the one already running is
  a violation. So is a command inside a transaction that legacy code opened, unless that call
  site is listed in tests/architecture/allowlists/legacy_tx_callers.toml. Django's own test-case
  transactions (marked _from_testcase) are ignored.
- **Violations.** With COMMAND_GUARD_STRICT on, a violation raises CrossModuleTransaction.
  Otherwise it logs a warning and adds 1 to violation_count(), and the command still runs.
- **Deadlocks** (MySQL error 1213) are retried only by the command that opened the outermost
  transaction, at most 3 attempts in all, 50 to 200 ms apart. A nested command re-raises so that
  the outermost one can retry.
"""

import functools
import inspect
import logging
import random
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


def _call_site() -> str:
    """The nearest caller outside building_blocks/ and modules/, as path/from/repo/root.py::function."""
    for frame in inspect.stack()[2:]:
        path = Path(frame.filename).resolve()
        if any(path.is_relative_to(directory) for directory in NEW_CODE):
            continue
        shown = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()
        return f"{shown}::{frame.function}"
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
            outermost = not running and not legacy_open
            attempts = MAX_ATTEMPTS if outermost else 1
            token = _owners.set((*running, owner))
            try:
                for attempt in range(1, attempts + 1):
                    try:
                        with transaction.atomic():
                            return function(*args, **kwargs)
                    except OperationalError as error:
                        if not _is_deadlock(error) or attempt == attempts:
                            raise
                        sleep(random.uniform(0.05, 0.2))
            finally:
                _owners.reset(token)

        return run

    return decorate
