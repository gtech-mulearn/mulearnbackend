"""Time-ordered UUIDv7 ids for new tables (RFC 9562 section 5.7, ADR-015).

Python 3.10's uuid module has no uuid7. The layout, most significant bit first:

    unix_ts_ms  48 bits  milliseconds since the Unix epoch
    ver          4 bits  0111
    rand_a      12 bits  the counter's high 12 bits
    var          2 bits  10, the RFC 4122 variant
    rand_b      62 bits  the counter's low 30 bits, then 32 random bits

The 42-bit counter is method 1 of RFC 9562 section 6.2. Each new millisecond starts it at a
random value with its top bit clear, and each further id in that millisecond adds one, so ids
from one process are strictly increasing:
- if the clock goes back, the last timestamp is reused;
- if the counter fills up, the timestamp moves on by one millisecond.

A forked child starts a fresh counter.
"""

import os
import threading
import time
import uuid

_VERSION_AND_VARIANT = 0x7 << 76 | 0b10 << 62
_COUNTER_MAX = (1 << 42) - 1

_lock = threading.Lock()
_last_ms = -1
_last_counter = 0


def _new_counter_and_tail() -> tuple[int, int]:
    """A random 42-bit counter with its top bit clear, and 32 random bits."""
    rand = int.from_bytes(os.urandom(10), "big")
    return (rand >> 32) & ((1 << 41) - 1), rand & 0xFFFF_FFFF


def _reset() -> None:
    global _last_ms, _last_counter
    _last_ms, _last_counter = -1, 0


def uuid7() -> uuid.UUID:
    """Return a new version 7 UUID, greater than every earlier one from this process."""
    global _last_ms, _last_counter
    with _lock:
        ms = time.time_ns() // 1_000_000
        if ms > _last_ms:
            counter, tail = _new_counter_and_tail()
        else:
            ms = _last_ms
            counter = _last_counter + 1
            if counter > _COUNTER_MAX:
                ms += 1
                counter, tail = _new_counter_and_tail()
            else:
                tail = int.from_bytes(os.urandom(4), "big")
        _last_ms, _last_counter = ms, counter
    value = (ms & 0xFFFF_FFFF_FFFF) << 80 | (counter >> 30) << 64 | (counter & 0x3FFF_FFFF) << 32 | tail
    return uuid.UUID(int=value | _VERSION_AND_VARIANT)


def uuid7_str() -> str:
    """Return a new version 7 UUID in its canonical 36-character form."""
    return str(uuid7())


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_reset)
