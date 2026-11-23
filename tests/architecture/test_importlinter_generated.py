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

    assert lines(parser["importlinter"]["root_packages"]) == ["building_blocks", "modules", *LEGACY]


def test_the_output_is_deterministic():
    assert render({}) == render({})


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


GRAPH_OF_TWO = {"events": [], "karma": ["events"]}


def test_each_module_gets_a_layers_contract_pointing_downwards():
    contract = contracts(render(GRAPH_OF_TWO))["events-layers"]

    assert contract["type"] == "layers"
    # Each layer is optional (in parentheses): a module without, say, adapters/ yet still lints.
    assert lines(contract["layers"]) == [
        "(modules.events.api) | (modules.events.tasks)",
        "(modules.events.services)",
        "(modules.events.selectors)",
        "(modules.events.data) | (modules.events.adapters)",
        "(modules.events.domain)",
    ]


def test_each_modules_domain_stays_framework_free():
    contract = contracts(render(GRAPH_OF_TWO))["karma-domain"]

    assert contract["type"] == "forbidden"
    assert lines(contract["source_modules"]) == ["modules.karma.domain"]
    assert lines(contract["forbidden_modules"]) == [
        "django",
        "rest_framework",
        "celery",
        "requests",
        "httpx",
        "opentelemetry",
        "building_blocks.persistence",
        "building_blocks.messaging",
        "building_blocks.http",
        "building_blocks.cache",
    ]


def test_a_declared_dependency_is_reached_only_through_public_and_contracts():
    contract = contracts(render(GRAPH_OF_TWO))["karma-boundaries"]

    assert lines(contract["forbidden_modules"]) == ["modules.events"]  # the whole module
    assert lines(contract["ignore_imports"]) == [
        "modules.karma -> modules.events.public",
        "modules.karma.** -> modules.events.public",
        "modules.karma -> modules.events.contracts",
        "modules.karma.** -> modules.events.contracts",
    ]
    assert contract["allow_indirect_imports"] == "True"


def test_an_undeclared_module_is_reached_only_through_contracts():
    contract = contracts(render(GRAPH_OF_TWO))["events-boundaries"]

    assert lines(contract["forbidden_modules"]) == ["modules.karma"]
    assert lines(contract["ignore_imports"]) == [
        "modules.events -> modules.karma.contracts",
        "modules.events.** -> modules.karma.contracts",
    ]


def test_modules_may_not_import_the_legacy_packages():
    contract = contracts(render({}))["modules-no-legacy"]

    assert contract["type"] == "forbidden"
    assert lines(contract["source_modules"]) == ["modules"]
    assert lines(contract["forbidden_modules"]) == LEGACY


def test_legacy_code_may_import_only_public_contracts_and_building_blocks():
    contract = contracts(render({}))["legacy-uses-public-surfaces"]

    assert contract["type"] == "forbidden"
    assert lines(contract["source_modules"]) == LEGACY
    assert lines(contract["forbidden_modules"]) == ["modules"]
    assert lines(contract["ignore_imports"]) == [
        f"{source} -> modules.*.{surface}"
        for package in LEGACY
        for source in (package, f"{package}.**")
        for surface in ("public", "contracts")
    ]
    assert contract["allow_indirect_imports"] == "True"


def test_a_dependency_on_an_undeclared_module_is_refused():
    with pytest.raises(ValueError, match="events -> people"):
        render({"events": ["people"]})


def test_module_contracts_are_in_a_stable_order():
    assert render({"b": [], "a": ["b"]}) == render({"a": ["b"], "b": []})
