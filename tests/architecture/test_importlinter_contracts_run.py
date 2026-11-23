"""Run lint-imports on small fixture trees with the contracts the generator writes.

The other tests check the generated text; these check that import-linter enforces it: the uses the
rules allow pass, and the ones they forbid fail (docs/architecture/04-module-rules.md).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.gen_importlinter import render

GRAPH = {"events": [], "contributions": ["events"]}
# Every layer but adapters: a missing layer must not break the run.
LAYER_PACKAGES = ("api", "tasks", "services", "selectors", "data", "domain")
PACKAGES = [
    "building_blocks",
    "api",
    "db",
    "utils",
    "mu_celery",
    "modules",
    *(f"modules.{module}.{part}" for module in GRAPH for part in LAYER_PACKAGES),
]
MODULE_FILES = [f"modules.{module}.{part}" for module in GRAPH for part in ("public", "contracts")]


def lint_imports() -> list[str]:
    found = shutil.which("lint-imports", path=str(Path(sys.executable).parent)) or shutil.which("lint-imports")
    assert found, "lint-imports isn't installed"
    return [found]


def write_tree(root: Path, files: dict[str, str]) -> None:
    for package in PACKAGES:
        path = root.joinpath(*package.split("."))
        path.mkdir(parents=True, exist_ok=True)
        (path / "__init__.py").touch()
    for module in GRAPH:
        (root / "modules" / module / "__init__.py").touch()
    for name in MODULE_FILES:
        root.joinpath(*name.split(".")).with_suffix(".py").touch()
    for name, source in files.items():
        path = root.joinpath(*name.split("."))
        target = path / "__init__.py" if path.is_dir() else path.with_suffix(".py")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")


def run(tmp_path: Path, files: dict[str, str]) -> subprocess.CompletedProcess:
    write_tree(tmp_path, files)
    (tmp_path / ".importlinter").write_text(render(GRAPH), encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(tmp_path)}
    return subprocess.run(
        [*lint_imports(), "--config", ".importlinter", "--no-cache"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


ALLOWED = {
    "a declared dependency on public, which imports its own selectors": {
        "modules.events.selectors.bookmarks": "",
        "modules.events.public": "from modules.events.selectors import bookmarks\n",
        "modules.contributions.services.notice": "from modules.events import public\n",
    },
    "any module's contracts, which import its domain": {
        "modules.events.domain.values": "",
        "modules.events.contracts": "from modules.events.domain import values\n",
        "modules.contributions.tasks.listen": "from modules.events import contracts\n",
    },
    "a legacy package's __init__ importing a public surface": {
        "api": "from modules.events import public\n",
    },
    "a module without an adapters package": {
        "modules.events.services.cancel": "from modules.events.selectors import x\n",
        "modules.events.selectors.x": "",
    },
}

FORBIDDEN = {
    "another module's file the anatomy doesn't name": {
        "modules.events.helpers": "",
        "modules.contributions.services.use": "from modules.events import helpers\n",
    },
    "an undeclared module's public": {
        "modules.events.services.use": "from modules.contributions import public\n",
    },
    "a module importing legacy code": {
        "modules.events.services.legacy_use": "import db\n",
    },
    "opentelemetry in a domain": {
        "modules.events.domain.otel": "import opentelemetry\n",
    },
}


@pytest.mark.parametrize("files", ALLOWED.values(), ids=ALLOWED.keys())
def test_lint_imports_allows(tmp_path, files):
    result = run(tmp_path, files)

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("files", FORBIDDEN.values(), ids=FORBIDDEN.keys())
def test_lint_imports_forbids(tmp_path, files):
    result = run(tmp_path, files)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "BROKEN" in result.stdout or "broken" in result.stdout.lower()
