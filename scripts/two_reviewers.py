"""Fail a pull request that touches a core-review path with fewer than two approvals (issue 0029).

    python scripts/two_reviewers.py <owner/repo> <pull request number>

Run by .github/workflows/two-reviewers.yml, which checks out this script from the base branch,
so a pull request can't change the rule it is checked against. It reads the pull request's
files and reviews with the GitHub CLI (GH_TOKEN). Exits 1 when the rule fails.
"""

import json
import subprocess
import sys

REQUIRED = 2
CORE_PATHS = (
    "building_blocks/authz/",
    "building_blocks/messaging/",
    "modules/contributions/",
    "modules/identity_access/",
    "scripts/deploy.sh",
    ".github/workflows/",
)
# Review states that set a reviewer's decision; a later COMMENTED review leaves it as it was.
DECISIONS = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}


def core_files(files: list[str]) -> list[str]:
    """The files under a core-review path, in the order given."""
    return [
        path
        for path in files
        if any(path == core if not core.endswith("/") else path.startswith(core) for core in CORE_PATHS)
    ]


def approvals(reviews: list[dict]) -> int:
    """How many reviewers' latest decision is an approval."""
    latest: dict[str, str] = {}
    for review in sorted(reviews, key=lambda r: r["id"]):
        if review["state"] in DECISIONS:
            latest[review["user"]["login"]] = review["state"]
    return sum(state == "APPROVED" for state in latest.values())


def decide(files: list[str], reviews: list[dict]) -> tuple[bool, str]:
    touched = core_files(files)
    if not touched:
        return True, "This pull request touches no core-review path: the usual one approval applies."
    count = approvals(reviews)
    listed = "\n".join(f"  {path}" for path in touched)
    if count >= REQUIRED:
        return True, f"Core-review paths touched, {count} approvals:\n{listed}"
    return False, (
        f"This pull request touches core-review paths and has {count} of {REQUIRED} required approvals:\n"
        f"{listed}\nAsk a second maintainer to review it (CONTRIBUTING.md, Branch rules)."
    )


def _api(path: str) -> list:
    output = subprocess.run(
        ["gh", "api", "--paginate", "--slurp", path], check=True, capture_output=True, text=True
    ).stdout
    return [item for page in json.loads(output) for item in page]


def main(argv: list[str]) -> int:
    repo, number = argv
    # A renamed file counts under its old path too: moving a file out of a core path is a core change.
    files = [
        path
        for item in _api(f"repos/{repo}/pulls/{number}/files")
        for path in (item["filename"], item.get("previous_filename"))
        if path
    ]
    reviews = _api(f"repos/{repo}/pulls/{number}/reviews")
    ok, message = decide(files, reviews)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
