"""The hashed lock files match the requirement pins (issue 0039).

requirements.lock is what the image installs; requirements-dev.lock (it includes everything in
requirements.lock, at the same versions) is what CI installs. After changing a requirements
file, regenerate both with the commands in their headers.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;\\]+)")


def normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def pins(path: Path) -> dict[str, str]:
    found = {}
    for line in (ROOT / path).read_text(encoding="utf-8").splitlines():
        match = PIN.match(line)
        if match:
            found[normalise(match.group(1))] = match.group(2)
    return found


def locked_entries(path: Path) -> dict[str, list[str]]:
    """Each locked package and its hash lines."""
    entries, current = {}, None
    for line in (ROOT / path).read_text(encoding="utf-8").splitlines():
        match = PIN.match(line)
        if match:
            current = normalise(match.group(1))
            entries[current] = []
        elif current and line.strip().startswith("--hash=sha256:"):
            entries[current].append(line.strip())
    return entries


def test_every_requirement_is_locked_at_its_pinned_version():
    lock = pins("requirements.lock")
    assert {name: version for name, version in pins("requirements.txt").items() if lock.get(name) != version} == {}


def test_every_dev_requirement_is_locked_at_its_pinned_version():
    lock = pins("requirements-dev.lock")
    dev = pins("requirements-dev.txt")
    assert {name: version for name, version in dev.items() if lock.get(name) != version} == {}


def test_ci_installs_the_same_versions_the_image_does():
    dev = pins("requirements-dev.lock")
    image = pins("requirements.lock")
    different = {name: (version, dev.get(name)) for name, version in image.items() if dev.get(name) != version}
    assert different == {}


def test_every_locked_package_has_a_hash():
    for path in ("requirements.lock", "requirements-dev.lock"):
        entries = locked_entries(path)
        assert entries, path
        assert [name for name, hashes in entries.items() if not hashes] == [], path


def test_the_unused_jwt_package_stays_removed():
    for path in ("requirements.txt", "requirements.lock", "requirements-dev.lock"):
        assert "djangorestframework-simplejwt" not in pins(path), path


def test_ci_and_the_image_install_with_hashes_and_a_pip_that_handles_extras():
    # pip before 24 rejects a dependency with extras, such as daphne's twisted[tls], in hash mode.
    for path, lock in ((".github/workflows/ci.yml", "requirements-dev.lock"), ("Dockerfile", "requirements.lock")):
        text = (ROOT / path).read_text(encoding="utf-8")
        assert f"--require-hashes -r {lock}" in text, path
        pip = re.search(r"pip install pip==(\d+)\.", text)
        assert pip and int(pip.group(1)) >= 24, path
