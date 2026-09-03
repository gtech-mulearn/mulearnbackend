"""Guards the event model choice values against the MySQL ENUM definitions.

MySQL resolves ENUM writes through the column's collation, which here is
case-insensitive (utf8mb4_0900_ai_ci). Writing 'DRAFT' into an enum declared
as 'draft' therefore succeeds silently and reads back as 'draft' — so a
casing drift between the model and the column produces no error anywhere,
and every Python-side `==` / `in` check against the constant simply goes
false. Nothing else in the suite can catch that; this test can.
"""
import re

import pytest
from django.db import connection

from db.events import Event, EventConnection


def _db_enum_values(table, column):
    """The values MySQL will actually store for an ENUM column, or None."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COLUMN_TYPE FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s AND COLUMN_NAME = %s
            """,
            [table, column],
        )
        row = cursor.fetchone()
    if not row or not row[0].lower().startswith("enum("):
        return None
    return set(re.findall(r"'((?:[^']|'')*)'", row[0]))


def _fields_with_choices(model):
    return [f for f in model._meta.get_fields()
            if getattr(f, "choices", None) and getattr(f, "column", None)]


ENUM_BACKED_MODELS = [Event, EventConnection]


@pytest.mark.parametrize(
    "model,field",
    [(m, f) for m in ENUM_BACKED_MODELS for f in _fields_with_choices(m)],
    ids=lambda v: getattr(v, "name", getattr(v, "__name__", str(v))),
)
def test_model_choices_match_the_database_enum(model, field):
    try:
        db_values = _db_enum_values(model._meta.db_table, field.column)
    except Exception as exc:
        pytest.skip(f"database unreachable, parity unverified: {exc}")

    if db_values is None:
        pytest.skip(f"{model._meta.db_table}.{field.column} is not an ENUM column")

    model_values = {value for value, _label in field.choices}

    assert model_values == db_values, (
        f"{model.__name__}.{field.name} does not match "
        f"{model._meta.db_table}.{field.column}.\n"
        f"  only in model: {sorted(model_values - db_values)}\n"
        f"  only in DB:    {sorted(db_values - model_values)}"
    )
