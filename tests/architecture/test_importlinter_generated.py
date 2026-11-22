import configparser

import pytest

from scripts.gen_importlinter import GRAPH, OUTPUT, load_graph, main, render

LEGACY = ["api", "db", "utils", "mu_celery"]


def contracts(text):
    parser = configparser.ConfigParser()
    parser.read_string(text)
    return {
        name.removeprefix("importlinter:contract:"): parser[name]
        for name in parser.sections()
        if name.startswith("importlinter:contract:")
    }


def lines(value):
    return [line.strip() for line in value.strip().splitlines()]


def test_the_committed_importlinter_matches_the_generator():
    assert OUTPUT.read_text(encoding="utf-8") == render(load_graph(GRAPH)), (
        ".importlinter is out of date: run python scripts/gen_importlinter.py"
    )


def test_building_blocks_may_not_import_business_or_legacy_code():
    contract = contracts(render({}))["building-blocks"]

    assert contract["type"] == "forbidden"
    assert lines(contract["source_modules"]) == ["building_blocks"]
    assert lines(contract["forbidden_modules"]) == ["modules", *LEGACY]


def test_the_legacy_packages_are_root_packages():
    parser = configparser.ConfigParser()
    parser.read_string(render({}))

    assert lines(parser["importlinter"]["root_packages"]) == ["building_blocks", *LEGACY]


def test_the_output_is_deterministic():
    assert render({}) == render({})


def test_the_graph_starts_with_no_modules():
    assert load_graph(GRAPH) == {}


def test_a_graph_without_a_modules_table_is_refused(tmp_path):
    graph = tmp_path / "module_graph.toml"
    graph.write_text("[other]\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"\[modules\]"):
        load_graph(graph)


def test_main_writes_the_rendered_file(tmp_path):
    graph = tmp_path / "module_graph.toml"
    graph.write_text("[modules]\n", encoding="utf-8")
    output = tmp_path / ".importlinter"

    assert main(["--graph", str(graph), "--output", str(output)]) == 0
    assert output.read_bytes() == render({}).encode("utf-8")
