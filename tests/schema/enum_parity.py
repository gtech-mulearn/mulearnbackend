"""Compare model choices with the schema's ENUM columns, case-sensitively (issue 0054).

MySQL compares ENUM values case-insensitively, but Python doesn't. So a choice that differs
from its ENUM value only in case writes fine and then fails every comparison silently. A choice
missing from the ENUM fails on write. An ENUM value without a choice is a value Python code
doesn't expect to read.

Known drift is recorded in known_drift.toml with an owner. The parity test fails on drift that
isn't recorded, and on a recorded entry that no longer drifts, so the file only shrinks.
"""

import re
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

KNOWN_DRIFT = Path(__file__).resolve().parent / "known_drift.toml"
KINDS = ("case_only", "missing_in_choices", "missing_in_enum", "no_choices")

_MESSAGES = {
    "case_only": "differ from the ENUM only in case: MySQL accepts them, then Python comparisons fail silently",
    "missing_in_enum": "are choices the ENUM doesn't allow: writing them fails",
    "missing_in_choices": "are ENUM values with no choice: Python code doesn't expect to read them",
    "no_choices": "are the ENUM's values, but the field has no choices: Python accepts any value and MySQL rejects it",
}


@dataclass(frozen=True, order=True)
class Drift:
    table: str
    column: str
    kind: str
    values: tuple[str, ...]

    def describe(self) -> str:
        return f"{self.table}.{self.column}: {list(self.values)} {_MESSAGES[self.kind]}"


def parse_enum(column_type: str) -> list[str]:
    """The values of an information_schema COLUMN_TYPE such as enum('a','it''s')."""
    inner = re.fullmatch(r"(?i)enum\((.*)\)", column_type.strip()).group(1)
    return [value.replace("''", "'") for value in re.findall(r"'((?:[^']|'')*)'", inner)]


def compare(table: str, column: str, choices: set[str], enum_values: list[str]) -> list[Drift]:
    """Every difference between a field's choice values and its column's ENUM values."""
    if not choices:
        return [Drift(table, column, "no_choices", tuple(sorted(enum_values)))]
    enum = set(enum_values)
    enum_folded = {value.casefold() for value in enum}
    choices_folded = {value.casefold() for value in choices}
    case_only = {value for value in choices - enum if value.casefold() in enum_folded}
    missing_in_enum = choices - enum - case_only
    missing_in_choices = {value for value in enum - choices if value.casefold() not in choices_folded}
    found = {"case_only": case_only, "missing_in_choices": missing_in_choices, "missing_in_enum": missing_in_enum}
    return [Drift(table, column, kind, tuple(sorted(found[kind]))) for kind in KINDS if found.get(kind)]


def load_known(path: Path = KNOWN_DRIFT) -> dict[Drift, str]:
    """The recorded drift, mapped to the module that owns each table."""
    with path.open("rb") as file:
        entries = tomllib.load(file).get("enum", [])
    known = {}
    for entry in entries:
        if not entry.get("owner"):
            raise ValueError(f"{path}: {entry.get('table')}.{entry.get('column')} needs an owner.")
        if entry["kind"] not in KINDS:
            raise ValueError(f"{path}: kind {entry['kind']!r} must be one of {', '.join(KINDS)}.")
        drift = Drift(entry["table"], entry["column"], entry["kind"], tuple(sorted(entry["values"])))
        known[drift] = entry["owner"]
    return known


def unexpected_and_fixed(actual: list[Drift], known: dict[Drift, str]) -> tuple[list[Drift], list[Drift]]:
    """Drift that isn't recorded, and recorded drift that's gone."""
    return sorted(set(actual) - set(known)), sorted(set(known) - set(actual))
