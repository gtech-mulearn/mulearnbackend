"""Compare unmanaged models with the loaded schema's information_schema (issue 0053, ADR-040).

Every model is managed = False, so nothing else checks that a model matches its table. A
difference shows up as a runtime error, such as 1054 "Unknown column", on the first query that
touches it. This reads information_schema only: it never changes the schema.

Known differences are the [[model]] entries in known_drift.toml, each with an owner. The parity
test fails on a difference that isn't listed and on a listed one that's gone, so the list only
shrinks.
"""

import importlib
import pkgutil
from dataclasses import dataclass

from django.apps import apps
from django.db import models

import db
from tests.schema.enum_parity import KNOWN_DRIFT, tomllib

KINDS = ("missing_table", "missing_column", "nullability", "max_length", "missing_foreign_key")

_MESSAGES = {
    "missing_table": "the table doesn't exist",
    "missing_column": "the column doesn't exist: every query that selects it fails with 1054",
    "nullability": "nullability differs",
    "max_length": "max_length is longer than the column",
    "missing_foreign_key": "the ForeignKey has no matching database foreign key",
}


@dataclass(frozen=True, order=True)
class Difference:
    table: str
    column: str
    kind: str
    detail: str

    def describe(self) -> str:
        where = self.table if not self.column else f"{self.table}.{self.column}"
        return f"{where}: {_MESSAGES[self.kind]} ({self.detail})" if self.detail else f"{where}: {_MESSAGES[self.kind]}"


@dataclass(frozen=True)
class Column:
    nullable: bool
    max_length: int | None
    data_type: str


@dataclass(frozen=True)
class Schema:
    """What information_schema says about the loaded database."""

    tables: frozenset[str]
    columns: dict[tuple[str, str], Column]
    foreign_keys: dict[tuple[str, str], tuple[str, str]]  # (table, column) -> (referenced table, column)


def read_schema(connection) -> Schema:
    with connection.cursor() as cursor:
        cursor.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()")
        tables = frozenset(row[0] for row in cursor.fetchall())
        cursor.execute(
            "SELECT TABLE_NAME, COLUMN_NAME, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH, DATA_TYPE"
            " FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
        )
        columns = {(t, c): Column(n == "YES", length, kind) for t, c, n, length, kind in cursor.fetchall()}
        cursor.execute(
            "SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME"
            " FROM information_schema.KEY_COLUMN_USAGE"
            " WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL"
        )
        foreign_keys = {(t, c): (rt, rc) for t, c, rt, rc in cursor.fetchall()}
    return Schema(tables, columns, foreign_keys)


def import_all_models() -> None:
    """Import every db module. db/models.py doesn't import them all, and a model registers only
    once its module is imported, so otherwise the models compared would depend on which tests
    ran first."""
    for module in pkgutil.iter_modules(db.__path__):
        importlib.import_module(f"db.{module.name}")


def unmanaged_models():
    """Every unmanaged model in db/."""
    import_all_models()
    return [
        model
        for model in apps.get_models()
        if not model._meta.managed and not model._meta.proxy and not model._meta.abstract
    ]


def compare_model(model, schema: Schema) -> list[Difference]:
    table = model._meta.db_table
    if table not in schema.tables:
        return [Difference(table, "", "missing_table", model._meta.label)]
    found = []
    for field in model._meta.concrete_fields:
        key = (table, field.column)
        column = schema.columns.get(key)
        if column is None:
            found.append(Difference(table, field.column, "missing_column", f"{model._meta.label}.{field.name}"))
            continue
        if field.null != column.nullable:
            model_side = "null=True" if field.null else "null=False"
            column_side = "NULL" if column.nullable else "NOT NULL"
            found.append(Difference(table, field.column, "nullability", f"model {model_side}, column {column_side}"))
        # An ENUM's length is its longest value; tests/schema/test_enum_parity.py checks ENUM columns.
        is_char = isinstance(field, models.CharField) and column.data_type != "enum"
        if is_char and field.max_length and column.max_length:
            if field.max_length > column.max_length:
                detail = f"model {field.max_length}, column {column.max_length}"
                found.append(Difference(table, field.column, "max_length", detail))
        if isinstance(field, models.ForeignKey) and field.db_constraint:
            target = (field.related_model._meta.db_table, field.target_field.column)
            if schema.foreign_keys.get(key) != target:
                actual = schema.foreign_keys.get(key)
                detail = f"to {target[0]}.{target[1]}"
                if actual:
                    detail += f"; the database has {actual[0]}.{actual[1]}"
                found.append(Difference(table, field.column, "missing_foreign_key", detail))
    return found


def compare_all(schema: Schema) -> list[Difference]:
    return sorted({difference for model in unmanaged_models() for difference in compare_model(model, schema)})


def load_known(path=KNOWN_DRIFT) -> dict[Difference, str]:
    """The [[model]] entries in known_drift.toml, mapped to their owners."""
    with path.open("rb") as file:
        entries = tomllib.load(file).get("model", [])
    known = {}
    for entry in entries:
        where = f"{entry.get('table')}.{entry.get('column', '')}"
        if not entry.get("owner"):
            raise ValueError(f"{path}: the [[model]] entry for {where} needs an owner.")
        if entry.get("kind") not in KINDS:
            raise ValueError(f"{path}: {where} has kind {entry.get('kind')!r}; use one of {', '.join(KINDS)}.")
        difference = Difference(entry["table"], entry.get("column", ""), entry["kind"], entry.get("detail", ""))
        known[difference] = entry["owner"]
    return known
