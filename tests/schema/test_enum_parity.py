"""Model choices match the schema's ENUM columns, case-sensitively (issue 0054)."""

import pytest
from django.apps import apps
from django.db import connection

from tests.schema.enum_parity import KNOWN_DRIFT, compare, load_known, parse_enum, unexpected_and_fixed

pytestmark = [pytest.mark.mysql, pytest.mark.django_db]


def enum_columns() -> dict[tuple[str, str], list[str]]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE FROM information_schema.COLUMNS"
            " WHERE TABLE_SCHEMA = DATABASE() AND DATA_TYPE = 'enum'"
        )
        return {(table, column): parse_enum(column_type) for table, column, column_type in cursor.fetchall()}


def mapped_fields(columns):
    """Every concrete model field whose column is an ENUM: ((table, column), field)."""
    for model in apps.get_models():
        for field in model._meta.concrete_fields:
            key = (model._meta.db_table, field.column)
            if key in columns:
                yield key, field


def test_model_choices_match_the_enum_columns_they_map():
    columns = enum_columns()
    drift = []
    for (table, column), field in mapped_fields(columns):
        choices = {str(value) for value, _ in field.flatchoices}
        drift += compare(table, column, choices, columns[(table, column)])
    unexpected, fixed = unexpected_and_fixed(drift, load_known())

    lines = []
    case_only = [d for d in unexpected if d.kind == "case_only"]
    others = [d for d in unexpected if d.kind != "case_only"]
    if case_only:
        lines += ["Case-only mismatches, the dangerous ones:"] + [f"  {d.describe()}" for d in case_only]
    if others:
        lines += ["Other enum mismatches:"] + [f"  {d.describe()}" for d in others]
    if unexpected:
        header = f"Enum drift that isn't recorded in {KNOWN_DRIFT.name}. Fix the model, or record it with an owner:"
        lines.insert(0, header)
    if fixed:
        lines += [f"Recorded drift that's fixed. Delete these entries from {KNOWN_DRIFT.name}:"]
        lines += [f"  {d.describe()}" for d in fixed]
    assert not lines, "\n".join(lines)


def test_the_enum_columns_are_found():
    assert ("events", "status") in enum_columns()
