import pytest
from django.core.exceptions import ImproperlyConfigured

from mulearnbackend.celery_schedules import select_schedules

SCHEDULE = {
    "intern-daily-status-cron": {"task": "a"},
    "refresh-leaderboards-cron": {"task": "b"},
    "push-dispatch-due-campaigns": {"task": "c"},
}


@pytest.mark.parametrize("selection", ["all", "ALL", " All ", "", "   "])
def test_all_or_empty_returns_every_entry(selection):
    assert select_schedules(SCHEDULE, selection) == SCHEDULE


def test_all_returns_a_new_dictionary():
    chosen = select_schedules(SCHEDULE, "all")
    assert chosen is not SCHEDULE


@pytest.mark.parametrize("selection", ["none", "NONE", " None "])
def test_none_returns_no_entries(selection):
    assert select_schedules(SCHEDULE, selection) == {}


def test_a_list_returns_exactly_those_entries():
    chosen = select_schedules(SCHEDULE, " refresh-leaderboards-cron , intern-daily-status-cron,,intern-daily-status-cron, ")
    assert chosen == {
        "refresh-leaderboards-cron": SCHEDULE["refresh-leaderboards-cron"],
        "intern-daily-status-cron": SCHEDULE["intern-daily-status-cron"],
    }


def test_unknown_names_raise_naming_each_one():
    with pytest.raises(ImproperlyConfigured) as error:
        select_schedules(SCHEDULE, "intern-daily-status-cron, typo-cron, other-typo")
    message = str(error.value)
    assert "typo-cron" in message
    assert "other-typo" in message


@pytest.mark.parametrize("selection", ["all, intern-daily-status-cron", "none,intern-daily-status-cron", "all,none"])
def test_all_or_none_combined_with_a_name_raises(selection):
    with pytest.raises(ImproperlyConfigured):
        select_schedules(SCHEDULE, selection)
