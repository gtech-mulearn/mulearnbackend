"""manage.py new_module <name> [--root <dir>]: create a module's layout (issue 0023).

The layout is "The anatomy of a module" in docs/architecture/04-module-rules.md. The name must be
in the module catalogue, docs/architecture/modules/README.md. The generator never overwrites a
module and never edits shared files; it prints the three steps that are the contributor's.
"""

import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

CATALOGUE = Path(settings.BASE_DIR) / "docs" / "architecture" / "modules" / "README.md"
NOT_MODULES = {"building_blocks"}  # in the catalogue, but not a package under modules/

PACKAGES = (
    "api",
    "services",
    "selectors",
    "data",
    "adapters",
    "domain",
    "management",
    "management/commands",
    "tests",
    "tests/domain",
    "tests/services",
    "tests/selectors",
    "tests/api",
    "tests/mysql",
)

APPS = """from django.apps import AppConfig


class {camel}Config(AppConfig):
    name = "modules.{name}"
    label = "{name}"
    verbose_name = "{title}"

    def ready(self):
        # Registers this module's policies. ready() never touches the database.
        from modules.{name} import policies  # noqa: F401
"""

DOCSTRINGS = {
    "public.py": "The only functions other modules may call (keep it under 25 names).\n\n"
    "It imports its parameter and return types from contracts.py and never defines them.",
    "contracts.py": "Every DTO and every versioned event of this module is defined here.\n\n"
    "A leaf: it imports only the standard library, building_blocks.messaging.events and domain/values.py.",
    "policies.py": "Authorization: one @policy per action of this module.",
    "tasks.py": "Celery tasks and event consumers: one line each, calling services.",
    "api/views.py": "Thin views: parse the request, call a service or selector, return the envelope.",
    "api/serializers.py": "Request and response shapes for this module's API.",
}

DOCS_PAGE = """# {name}

> Created by `python manage.py new_module {name}`. Fill in each section as the module grows.

## Owns

The tables this module owns, and only this module writes.

## Public API

The functions in `modules/{name}/public.py`, with the DTOs from `contracts.py`.

## Events

The events this module publishes and consumes.

## Issues

The issues that build this module.
"""


def catalogue_names() -> set[str]:
    text = CATALOGUE.read_text(encoding="utf-8")
    return set(re.findall(r"^\| \[([a-z_]+)\]\([a-z_]+\.md\) \|", text, flags=re.MULTILINE)) - NOT_MODULES


class Command(BaseCommand):
    help = "Create a module's layout under modules/<name>/. The name must be in the module catalogue."

    def add_arguments(self, parser):
        parser.add_argument("name")
        parser.add_argument("--root", default=str(settings.BASE_DIR), help="The repository root to write into.")

    def handle(self, *args, name, root, **options):
        if name not in catalogue_names():
            raise CommandError(
                f"{name!r} isn't in the module catalogue (docs/architecture/modules/README.md). "
                "Add it there first, through architecture review."
            )
        root = Path(root)
        module = root / "modules" / name
        if module.exists():
            raise CommandError(f"modules/{name} already exists: the generator never overwrites a module.")

        files = {"__init__.py": f'"""The {name} module (docs/architecture/modules/{name}.md)."""\n'}
        files["apps.py"] = APPS.format(
            name=name, camel=name.title().replace("_", ""), title=name.replace("_", " ").title()
        )
        for path, docstring in DOCSTRINGS.items():
            files[path] = f'"""{docstring}"""\n'
        files["api/urls.py"] = f'"""Routes of the {name} module, mounted by modules/urls.py."""\n\nurlpatterns = []\n'
        for package in PACKAGES:
            files.setdefault(f"{package}/__init__.py", "")

        for relative, text in sorted(files.items()):
            path = module / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        self.stdout.write(f"Created modules/{name}/ ({len(files)} files).")

        page = root / "docs" / "architecture" / "modules" / f"{name}.md"
        if not page.exists():
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(DOCS_PAGE.format(name=name), encoding="utf-8", newline="\n")
            self.stdout.write(f"Created docs/architecture/modules/{name}.md.")

        self.stdout.write(
            "Next, by hand (the generator never edits shared files):\n"
            f"  1. Declare it in tests/architecture/module_graph.toml: {name} = [...], then run "
            "python scripts/gen_importlinter.py.\n"
            f'  2. Mount its routes in modules/urls.py: path("{name}/", include("modules.{name}.api.urls")).\n'
            f'  3. Add "modules.{name}" to INSTALLED_APPS in mulearnbackend/settings.py.'
        )
