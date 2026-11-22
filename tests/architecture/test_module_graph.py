"""The module graph is acyclic and matches the packages under modules/ (issue 0023)."""

from pathlib import Path

from scripts.gen_importlinter import GRAPH, load_graph
from tests.architecture.graph import cycle, declared_but_missing, module_packages, undeclared, unknown_dependencies

ROOT = Path(__file__).resolve().parents[2]


def test_the_graph_is_acyclic():
    assert cycle(load_graph(GRAPH)) is None


def test_every_package_under_modules_is_declared():
    assert undeclared(load_graph(GRAPH), module_packages(ROOT)) == []


def test_every_declared_module_exists():
    assert declared_but_missing(load_graph(GRAPH), module_packages(ROOT)) == []


def test_every_dependency_is_a_declared_module():
    assert unknown_dependencies(load_graph(GRAPH)) == []


def test_a_cycle_is_found():
    assert cycle({"a": ["b"], "b": ["c"], "c": ["a"], "d": []}) == ["a", "b", "c", "a"]
    assert cycle({"a": ["a"]}) == ["a", "a"]
    assert cycle({"a": ["b"], "b": [], "c": ["a", "b"]}) is None


def test_an_undeclared_module_is_found(tmp_path):
    for name in ("events", "karma"):
        (tmp_path / "modules" / name).mkdir(parents=True)
        (tmp_path / "modules" / name / "__init__.py").touch()
    (tmp_path / "modules" / "not_a_package").mkdir()

    assert module_packages(tmp_path) == {"events", "karma"}
    assert undeclared({"events": []}, module_packages(tmp_path)) == ["karma"]
    assert declared_but_missing({"events": [], "people": []}, module_packages(tmp_path)) == ["people"]


def test_an_unknown_dependency_is_found():
    assert unknown_dependencies({"events": ["people"], "karma": []}) == ["events -> people"]
