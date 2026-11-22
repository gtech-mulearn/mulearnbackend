import ast
import os
import sys
import threading
import time
import uuid
from pathlib import Path

import pytest

from building_blocks import ids
from building_blocks.ids import uuid7, uuid7_str

MAX_COUNTER = (1 << 42) - 1


def counter(value: uuid.UUID) -> int:
    """The 42-bit counter: rand_a (12 bits), then the top 30 bits of rand_b."""
    return ((value.int >> 64) & 0xFFF) << 30 | (value.int >> 32) & 0x3FFF_FFFF


def test_the_version_is_7_and_the_variant_is_rfc_4122():
    value = uuid7()

    assert value.version == 7
    assert value.variant == uuid.RFC_4122


def test_the_first_48_bits_are_the_unix_time_in_milliseconds():
    before = time.time_ns() // 1_000_000
    value = uuid7()
    after = time.time_ns() // 1_000_000

    assert before <= value.int >> 80 <= after


def test_ten_thousand_ids_from_one_process_are_strictly_increasing():
    values = [uuid7() for _ in range(10_000)]

    assert all(a < b for a, b in zip(values, values[1:], strict=False))


def test_ids_from_several_threads_are_unique():
    values = []

    def generate():
        values.extend(uuid7() for _ in range(2_500))

    threads = [threading.Thread(target=generate) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(set(values)) == 10_000


def test_ids_keep_increasing_when_the_clock_goes_back(monkeypatch):
    now = time.time_ns()
    first = uuid7()
    monkeypatch.setattr(ids.time, "time_ns", lambda: now - 5_000_000_000)

    assert uuid7() > first


def test_a_full_counter_moves_on_to_the_next_millisecond(monkeypatch):
    now = time.time_ns()
    monkeypatch.setattr(ids.time, "time_ns", lambda: now)
    monkeypatch.setattr(ids, "_new_counter_and_tail", lambda: (MAX_COUNTER, 0))
    ids._reset()
    first = uuid7()
    second = uuid7()

    assert counter(first) == MAX_COUNTER
    assert second > first
    assert second.int >> 80 == (first.int >> 80) + 1


def test_a_new_millisecond_starts_with_a_counter_that_has_room_to_grow():
    # RFC 9562 section 6.2: the counter's top bit starts at 0, so it can't overflow at once.
    ids._reset()

    assert counter(uuid7()) < 1 << 41


@pytest.mark.skipif(not hasattr(os, "fork"), reason="needs os.fork")
def test_a_forked_child_starts_a_new_counter():
    parent = uuid7()
    read, write = os.pipe()
    pid = os.fork()
    if pid == 0:  # pragma: no cover - runs in the child
        os.write(write, uuid7().bytes)
        os._exit(0)
    os.waitpid(pid, 0)
    child = uuid.UUID(bytes=os.read(read, 16))

    assert counter(child) != counter(parent) + 1


def test_the_string_form_is_canonical():
    value = uuid7_str()

    assert len(value) == 36
    assert str(uuid.UUID(value)) == value
    assert uuid.UUID(value).version == 7


def test_the_module_imports_only_the_standard_library():
    imported = set()
    for node in ast.walk(ast.parse(Path(ids.__file__).read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    assert imported
    assert imported <= set(sys.stdlib_module_names)
