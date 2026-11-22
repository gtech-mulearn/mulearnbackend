"""The comparison behind the enum parity test, on the unit tier (issue 0054)."""

import pytest

from tests.schema.enum_parity import Drift, compare, load_known, parse_enum, unexpected_and_fixed


@pytest.mark.parametrize(
    ("column_type", "values"),
    [
        ("enum('a','b')", ["a", "b"]),
        ("enum('Pending Approval','In-Review')", ["Pending Approval", "In-Review"]),
        ("enum('it''s','x')", ["it's", "x"]),
        ("ENUM('a')", ["a"]),
    ],
)
def test_enum_column_types_are_parsed(column_type, values):
    assert parse_enum(column_type) == values


def test_matching_values_have_no_drift():
    assert compare("t", "c", {"a", "b"}, ["a", "b"]) == []


def test_a_choice_missing_from_the_enum_is_drift():
    assert compare("t", "c", {"a", "b", "z"}, ["a", "b"]) == [Drift("t", "c", "missing_in_enum", ("z",))]


def test_an_enum_value_without_a_choice_is_drift():
    assert compare("t", "c", {"a"}, ["a", "b"]) == [Drift("t", "c", "missing_in_choices", ("b",))]


def test_a_case_only_mismatch_is_reported_on_its_own():
    drift = compare("t", "status", {"PENDING", "done"}, ["pending", "done"])

    assert drift == [Drift("t", "status", "case_only", ("PENDING",))]
    assert "case" in drift[0].describe()
    assert "silently" in drift[0].describe()


def test_case_only_and_missing_values_are_separate_entries():
    drift = compare("t", "c", {"A", "z"}, ["a", "b"])

    assert drift == [
        Drift("t", "c", "case_only", ("A",)),
        Drift("t", "c", "missing_in_choices", ("b",)),
        Drift("t", "c", "missing_in_enum", ("z",)),
    ]


def test_a_field_without_choices_on_an_enum_column_is_drift():
    assert compare("t", "c", set(), ["b", "a"]) == [Drift("t", "c", "no_choices", ("a", "b"))]


def test_known_drift_is_read_with_owners(tmp_path):
    path = tmp_path / "known_drift.toml"
    path.write_text(
        '[[enum]]\ntable = "t"\ncolumn = "c"\nkind = "case_only"\nvalues = ["A"]\nowner = "events"\n',
        encoding="utf-8",
    )

    assert load_known(path) == {Drift("t", "c", "case_only", ("A",)): "events"}


def test_known_drift_without_an_owner_is_refused(tmp_path):
    path = tmp_path / "known_drift.toml"
    path.write_text('[[enum]]\ntable = "t"\ncolumn = "c"\nkind = "case_only"\nvalues = ["A"]\n', encoding="utf-8")

    with pytest.raises(ValueError, match="owner"):
        load_known(path)


def test_new_drift_and_fixed_entries_are_both_found():
    known = {Drift("t", "a", "case_only", ("X",)): "events", Drift("t", "b", "missing_in_enum", ("y",)): "events"}
    actual = [Drift("t", "a", "case_only", ("X",)), Drift("t", "c", "missing_in_enum", ("z",))]

    unexpected, fixed = unexpected_and_fixed(actual, known)

    assert unexpected == [Drift("t", "c", "missing_in_enum", ("z",))]
    assert fixed == [Drift("t", "b", "missing_in_enum", ("y",))]
