import json
from pathlib import Path

import pytest

from scripts.two_reviewers import CORE_PATHS, approvals, core_files, decide

ROOT = Path(__file__).resolve().parents[1]


def review(user, state, review_id):
    return {"id": review_id, "user": {"login": user}, "state": state}


def test_core_files_lists_only_the_files_under_a_core_path():
    files = [
        "building_blocks/authz/policy.py",
        "building_blocks/errors.py",
        "modules/contributions/domain.py",
        "modules/events/domain.py",
        "scripts/deploy.sh",
        "scripts/deploy.sh.bak",
        ".github/workflows/ci.yml",
        "docs/architecture/README.md",
    ]

    assert core_files(files) == [
        "building_blocks/authz/policy.py",
        "modules/contributions/domain.py",
        "scripts/deploy.sh",
        ".github/workflows/ci.yml",
    ]


def test_the_core_paths_are_the_ones_issue_0029_names():
    assert set(CORE_PATHS) == {
        "building_blocks/authz/",
        "building_blocks/messaging/",
        "modules/contributions/",
        "modules/identity_access/",
        "scripts/deploy.sh",
        ".github/workflows/",
    }


def test_approvals_counts_each_reviewers_latest_decision():
    reviews = [
        review("asha", "APPROVED", 1),
        review("ben", "CHANGES_REQUESTED", 2),
        review("ben", "APPROVED", 3),
        review("chitra", "APPROVED", 4),
        review("chitra", "DISMISSED", 5),
        review("dev", "COMMENTED", 6),
    ]

    assert approvals(reviews) == 2  # asha, and ben's later approval; chitra's was dismissed


def test_a_comment_after_an_approval_keeps_the_approval():
    assert approvals([review("asha", "APPROVED", 1), review("asha", "COMMENTED", 2)]) == 1


def test_a_pull_request_without_a_core_path_passes_with_no_approvals():
    ok, message = decide(["api/dashboard/views.py"], [])

    assert ok
    assert "no core-review path" in message


def test_a_core_path_with_one_approval_fails():
    ok, message = decide(["building_blocks/authz/policy.py"], [review("asha", "APPROVED", 1)])

    assert not ok
    assert "1 of 2" in message
    assert "building_blocks/authz/policy.py" in message


def test_a_core_path_with_two_approvals_passes():
    ok, _ = decide(
        ["building_blocks/authz/policy.py"],
        [review("asha", "APPROVED", 1), review("ben", "APPROVED", 2)],
    )

    assert ok


@pytest.mark.parametrize("branch", ["dev", "staging", "production"])
def test_each_ruleset_requires_a_pull_request_an_approval_the_checks_and_forbids_force_pushes(branch):
    ruleset = json.loads((ROOT / ".github" / "rulesets" / f"{branch}.json").read_text(encoding="utf-8"))
    rules = {rule["type"]: rule.get("parameters", {}) for rule in ruleset["rules"]}

    assert ruleset["conditions"]["ref_name"]["include"] == [f"refs/heads/{branch}"]
    assert ruleset["enforcement"] == "active"
    assert ruleset["bypass_actors"] == []  # urgent fixes go through the same rules
    assert rules["pull_request"]["required_approving_review_count"] >= 1
    assert {"deletion", "non_fast_forward"} <= set(rules)
    checks = {check["context"] for check in rules["required_status_checks"]["required_status_checks"]}
    assert {"unit", "mysql (8.0)", "mysql (8.4)", "two reviewers"} <= checks
