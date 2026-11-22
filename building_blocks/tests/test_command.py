import logging

import pytest
from django.db import OperationalError, connection, transaction

from building_blocks.persistence import command as command_module
from building_blocks.persistence.command import CrossModuleTransaction, command, current_owners, violation_count
from tests.command_callers import legacy_caller

CALL_SITE = "tests/command_callers.py::legacy_caller"

# No outer transaction. available_apps keeps the flush after each test to building_blocks, which
# has no tables: the SQLite tier lacks the schema tables the other apps' models point at.
transactional = pytest.mark.django_db(transaction=True, available_apps=["building_blocks"])


@pytest.fixture
def strict(settings):
    settings.COMMAND_GUARD_STRICT = True


@pytest.fixture
def lenient(settings):
    settings.COMMAND_GUARD_STRICT = False


@pytest.fixture
def listed(monkeypatch):
    """Allow the stand-in legacy caller."""
    monkeypatch.setattr(command_module, "legacy_callers", lambda: frozenset({CALL_SITE}))


@pytest.fixture
def unlisted(monkeypatch):
    monkeypatch.setattr(command_module, "legacy_callers", lambda: frozenset())


def deadlock():
    return OperationalError(1213, "Deadlock found when trying to get lock; try restarting transaction")


@pytest.mark.django_db
def test_nested_commands_with_the_same_owner_are_fine(strict):
    @command("events")
    def inner():
        return current_owners()

    @command("events")
    def outer():
        return inner()

    assert outer() == ("events", "events")


@pytest.mark.django_db
def test_a_command_of_another_module_inside_a_command_raises_when_strict(strict):
    @command("karma")
    def inner():
        return "ran"

    @command("events")
    def outer():
        return inner()

    with pytest.raises(CrossModuleTransaction, match="karma.*events"):
        outer()


@pytest.mark.django_db
def test_a_cross_module_call_only_logs_and_counts_when_not_strict(lenient, caplog):
    @command("karma")
    def inner():
        return "ran"

    @command("events")
    def outer():
        return inner()

    before = violation_count()
    with caplog.at_level(logging.WARNING, logger="building_blocks.persistence"):
        assert outer() == "ran"

    assert violation_count() == before + 1
    assert "karma" in caplog.text and "events" in caplog.text


@pytest.mark.django_db
def test_a_command_inside_a_legacy_transaction_from_an_unlisted_site_raises(strict, unlisted):
    @command("events")
    def write():
        return "ran"

    with pytest.raises(CrossModuleTransaction, match=CALL_SITE):
        legacy_caller(write)


@pytest.mark.django_db
def test_a_command_inside_a_legacy_transaction_from_a_listed_site_runs(strict, listed):
    @command("events")
    def write():
        return "ran"

    assert legacy_caller(write) == "ran"


@pytest.mark.django_db
def test_the_test_cases_own_transaction_isnt_a_legacy_one(strict, unlisted):
    @command("events")
    def write():
        return "ran"

    assert connection.atomic_blocks  # pytest-django's test case is inside one
    assert write() == "ran"


@transactional
def test_a_command_called_outside_any_transaction_opens_one(strict):
    seen = {}

    @command("events")
    def write():
        seen["in_atomic_block"] = connection.in_atomic_block
        return "ran"

    assert not connection.in_atomic_block
    assert write() == "ran"
    assert seen == {"in_atomic_block": True}


@transactional
def test_a_deadlock_is_retried_at_the_outermost_level_three_times_in_all(strict):
    calls, pauses = [], []

    @command("events", sleep=pauses.append)
    def write():
        calls.append(1)
        raise deadlock()

    with pytest.raises(OperationalError):
        write()

    assert len(calls) == 3
    assert len(pauses) == 2
    assert all(0.05 <= pause <= 0.2 for pause in pauses)


@transactional
def test_a_deadlock_that_clears_is_retried_until_it_succeeds(strict):
    calls = []

    @command("events", sleep=lambda seconds: None)
    def write():
        calls.append(1)
        if len(calls) < 2:
            raise deadlock()
        return "ran"

    assert write() == "ran"
    assert len(calls) == 2


@transactional
def test_a_nested_command_doesnt_retry(strict):
    inner_calls, outer_calls = [], []

    @command("events", sleep=lambda seconds: None)
    def inner():
        inner_calls.append(1)
        raise deadlock()

    @command("events", sleep=lambda seconds: None)
    def outer():
        outer_calls.append(1)
        return inner()

    with pytest.raises(OperationalError):
        outer()

    # Only the outermost command retries: each of its 3 attempts calls inner once.
    assert len(outer_calls) == 3
    assert len(inner_calls) == 3


@transactional
def test_other_operational_errors_arent_retried(strict):
    calls = []

    @command("events", sleep=lambda seconds: None)
    def write():
        calls.append(1)
        raise OperationalError(2006, "MySQL server has gone away")

    with pytest.raises(OperationalError):
        write()
    assert len(calls) == 1


@pytest.mark.django_db
def test_the_stack_is_empty_after_an_exception(strict):
    @command("events")
    def write():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        write()

    assert current_owners() == ()


@pytest.mark.django_db
def test_the_decorator_works_on_a_method(strict):
    class Service:
        def __init__(self):
            self.name = "service"

        @command("events")
        def save(self, value):
            """Save the value."""
            return (self.name, value, current_owners())

    assert Service().save(3) == ("service", 3, ("events",))
    assert Service.save.__name__ == "save"
    assert Service.save.__doc__ == "Save the value."


@pytest.mark.django_db
def test_a_violation_outside_strict_mode_still_runs_the_command_inside_a_transaction(lenient, unlisted):
    @command("events")
    def write():
        return connection.in_atomic_block

    with transaction.atomic():
        assert write() is True


def test_the_legacy_caller_allowlist_starts_empty():
    command_module.legacy_callers.cache_clear()

    assert command_module.legacy_callers() == frozenset()
