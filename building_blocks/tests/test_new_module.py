import py_compile

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

PACKAGES = [
    "",
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
]
FILES = [
    "apps.py",
    "public.py",
    "contracts.py",
    "policies.py",
    "tasks.py",
    "api/views.py",
    "api/serializers.py",
    "api/urls.py",
]
EXPECTED = {f"modules/events/{p}/__init__.py".replace("//", "/") for p in PACKAGES} | {
    f"modules/events/{f}" for f in FILES
}


def tree(root):
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def test_new_module_creates_the_layout(tmp_path):
    call_command("new_module", "events", "--root", str(tmp_path))

    assert tree(tmp_path) == EXPECTED | {"docs/architecture/modules/events.md"}


def test_the_generated_python_compiles_and_names_the_app(tmp_path):
    call_command("new_module", "events", "--root", str(tmp_path))

    for path in (tmp_path / "modules" / "events").rglob("*.py"):
        py_compile.compile(str(path), doraise=True)
    apps = (tmp_path / "modules/events/apps.py").read_text(encoding="utf-8")
    assert "class EventsConfig(AppConfig):" in apps
    assert 'name = "modules.events"' in apps
    assert "urlpatterns = []" in (tmp_path / "modules/events/api/urls.py").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["eventz", "Events", "building_blocks", "../events", ""])
def test_a_name_outside_the_catalogue_is_refused(tmp_path, name):
    with pytest.raises(CommandError, match="catalogue"):
        call_command("new_module", name, "--root", str(tmp_path))

    assert tree(tmp_path) == set()


def test_an_existing_module_is_never_overwritten(tmp_path):
    existing = tmp_path / "modules/events/public.py"
    existing.parent.mkdir(parents=True)
    existing.write_text("# mine\n", encoding="utf-8")

    with pytest.raises(CommandError, match="already exists"):
        call_command("new_module", "events", "--root", str(tmp_path))

    assert existing.read_text(encoding="utf-8") == "# mine\n"
    assert tree(tmp_path) == {"modules/events/public.py"}


def test_an_existing_docs_page_is_kept(tmp_path):
    page = tmp_path / "docs/architecture/modules/events.md"
    page.parent.mkdir(parents=True)
    page.write_text("# events, by hand\n", encoding="utf-8")

    call_command("new_module", "events", "--root", str(tmp_path))

    assert page.read_text(encoding="utf-8") == "# events, by hand\n"


def test_shared_files_are_never_edited(tmp_path, capsys):
    shared = {
        "modules/urls.py": "urlpatterns = []\n",
        "tests/architecture/module_graph.toml": "[modules]\n",
        "mulearnbackend/settings.py": "INSTALLED_APPS = []\n",
    }
    for path, text in shared.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text, encoding="utf-8")

    call_command("new_module", "events", "--root", str(tmp_path))

    assert {path: (tmp_path / path).read_text(encoding="utf-8") for path in shared} == shared
    out = capsys.readouterr().out
    assert "module_graph.toml" in out and "modules/urls.py" in out and "INSTALLED_APPS" in out
