import json
from pathlib import Path

import pytest
import yaml

from scripts import two_reviewers
from scripts.two_reviewers import CORE_PATHS, approvals, core_files, decide

ROOT = Path(__file__).resolve().parents[1]


def review(user, state, review_id, association="MEMBER", kind="User"):
    return {"id": review_id, "user": {"login": user, "type": kind}, "state": state, "author_association": association}


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


def test_only_approvals_from_people_with_access_count():
    reviews = [
        review("maintainer", "APPROVED", 1, association="MEMBER"),
        review("outsider", "APPROVED", 2, association="NONE"),
        review("contributor", "APPROVED", 3, association="CONTRIBUTOR"),
        review("github-actions[bot]", "APPROVED", 4, association="NONE", kind="Bot"),
        review("collab", "APPROVED", 5, association="COLLABORATOR"),
    ]

    assert approvals(reviews) == 2  # maintainer and collab


def test_a_review_by_a_deleted_account_is_skipped():
    reviews = [{"id": 1, "user": None, "state": "APPROVED", "author_association": "NONE"}]

    assert approvals(reviews) == 0


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
    assert rules["pull_request"]["dismiss_stale_reviews_on_push"] is True
    # Code owners (CODEOWNERS) must approve their paths, .github/workflows/ included: a pull request
    # can't edit the two-reviewers workflow away with an outsider's approval.
    assert rules["pull_request"]["require_code_owner_review"] is True
    assert {"deletion", "non_fast_forward"} <= set(rules)
    checks = rules["required_status_checks"]["required_status_checks"]
    assert {check["context"] for check in checks} == {"unit", "legacy", "mysql (8.0)", "mysql (8.4)", "two reviewers"}
    # Only GitHub Actions may satisfy them, so a commit status of the same name can't stand in.
    assert all(check["integration_id"] == 15368 for check in checks)


def test_the_required_checks_are_the_job_names_ci_produces():
    ci = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    reviewers = yaml.safe_load((ROOT / ".github" / "workflows" / "two-reviewers.yml").read_text(encoding="utf-8"))
    names = {job.get("name", key) for key, job in ci["jobs"].items()}
    names = {name.replace("${{ matrix.mysql }}", version) for name in names for version in ("8.0", "8.4")}
    names |= {job["name"] for job in reviewers["jobs"].values()}
    ruleset = json.loads((ROOT / ".github" / "rulesets" / "dev.json").read_text(encoding="utf-8"))
    rules = {rule["type"]: rule.get("parameters", {}) for rule in ruleset["rules"]}

    assert {check["context"] for check in rules["required_status_checks"]["required_status_checks"]} <= names


def test_the_workflow_runs_the_default_branchs_script():
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "two-reviewers.yml").read_text(encoding="utf-8"))
    checkout = workflow["jobs"]["two-reviewers"]["steps"][0]

    assert checkout["with"]["ref"] == "${{ github.event.repository.default_branch }}"


def fake_api(pull, files, reviews):
    def api(path):
        resource = path.split("?")[0]
        if resource.endswith("/files"):
            return files
        if resource.endswith("/reviews"):
            return reviews
        return pull

    return api


def test_main_counts_a_renamed_files_old_path(capsys):
    files = [{"filename": "building_blocks/policy_moved.py", "previous_filename": "building_blocks/authz/policy.py"}]
    api = fake_api({"changed_files": 1}, files, [review("asha", "APPROVED", 1)])

    assert two_reviewers.main(["gtech-mulearn/mulearnbackend", "1"], api=api) == 1
    assert "building_blocks/authz/policy.py" in capsys.readouterr().out


def test_main_treats_an_incomplete_file_list_as_core(capsys):
    # GitHub lists at most 3000 files: a pull request with more might hide a core path.
    api = fake_api({"changed_files": 3500}, [{"filename": "api/x.py"}], [review("asha", "APPROVED", 1)])

    assert two_reviewers.main(["gtech-mulearn/mulearnbackend", "1"], api=api) == 1
    assert "3500" in capsys.readouterr().out


def test_main_passes_a_pull_request_without_core_paths():
    api = fake_api({"changed_files": 1}, [{"filename": "api/x.py"}], [])

    assert two_reviewers.main(["gtech-mulearn/mulearnbackend", "1"], api=api) == 0


def test_the_api_helper_flattens_the_pages(monkeypatch):
    class Done:
        stdout = json.dumps([[{"n": 1}, {"n": 2}], [{"n": 3}]])

    monkeypatch.setattr(two_reviewers.subprocess, "run", lambda *args, **kwargs: Done())

    assert two_reviewers._api("repos/x/pulls/1/files") == [{"n": 1}, {"n": 2}, {"n": 3}]
