"""The comparison behind the model/DDL parity test, on the unit tier (issue 0053)."""

import pytest

from db.user import Role
from tests.schema.model_parity import Column, Difference, Schema, compare_model, load_known

TABLE = "role"


def role_schema(drop=(), columns=None, foreign_keys=None, tables=(TABLE, "user")):
    """A schema in which the role table matches the Role model exactly, unless changed."""
    exact = {
        "id": Column(False, 36, "varchar"),
        "title": Column(False, 75, "varchar"),
        "description": Column(True, 300, "varchar"),
        "updated_by": Column(False, 36, "varchar"),
        "updated_at": Column(False, None, "datetime"),
        "created_by": Column(False, 36, "varchar"),
        "created_at": Column(False, None, "datetime"),
        "is_execom_role": Column(False, None, "tinyint"),
    }
    exact.update(columns or {})
    fks = {(TABLE, "updated_by"): ("user", "id"), (TABLE, "created_by"): ("user", "id")}
    fks.update(foreign_keys or {})
    return Schema(
        frozenset(tables),
        {(TABLE, name): column for name, column in exact.items() if name not in drop},
        {key: target for key, target in fks.items() if target is not None},
    )


def test_a_model_that_matches_its_table_has_no_differences():
    assert compare_model(Role, role_schema()) == []


def test_a_missing_table_is_one_difference():
    assert compare_model(Role, role_schema(tables=("user",))) == [Difference(TABLE, "", "missing_table", "db.Role")]


def test_a_model_field_without_its_column_is_found():
    # The acceptance case: a field added to a model whose column doesn't exist.
    assert compare_model(Role, role_schema(drop=("description",))) == [
        Difference(TABLE, "description", "missing_column", "db.Role.description")
    ]


@pytest.mark.parametrize(
    ("column", "detail"),
    [
        (Column(False, 300, "varchar"), "model null=True, column NOT NULL"),
    ],
)
def test_a_nullable_field_on_a_not_null_column_is_found(column, detail):
    assert compare_model(Role, role_schema(columns={"description": column})) == [
        Difference(TABLE, "description", "nullability", detail)
    ]


def test_a_required_field_on_a_nullable_column_is_found():
    assert compare_model(Role, role_schema(columns={"title": Column(True, 75, "varchar")})) == [
        Difference(TABLE, "title", "nullability", "model null=False, column NULL")
    ]


def test_a_char_field_longer_than_its_column_is_found():
    assert compare_model(Role, role_schema(columns={"title": Column(False, 50, "varchar")})) == [
        Difference(TABLE, "title", "max_length", "model 75, column 50")
    ]


def test_a_char_field_shorter_than_its_column_is_fine():
    assert compare_model(Role, role_schema(columns={"title": Column(False, 255, "varchar")})) == []


def test_an_enum_columns_length_is_left_to_the_enum_parity_test():
    assert compare_model(Role, role_schema(columns={"title": Column(False, 5, "enum")})) == []


def test_a_foreign_key_without_a_database_constraint_is_found():
    assert compare_model(Role, role_schema(foreign_keys={(TABLE, "created_by"): None})) == [
        Difference(TABLE, "created_by", "missing_foreign_key", "to user.id")
    ]


def test_a_database_foreign_key_to_another_table_is_found():
    assert compare_model(Role, role_schema(foreign_keys={(TABLE, "created_by"): ("college", "id")})) == [
        Difference(TABLE, "created_by", "missing_foreign_key", "to user.id; the database has college.id")
    ]


def test_a_foreign_key_declared_without_a_constraint_isnt_checked(monkeypatch):
    monkeypatch.setattr(Role._meta.get_field("created_by"), "db_constraint", False)

    assert compare_model(Role, role_schema(foreign_keys={(TABLE, "created_by"): None})) == []


def test_every_entry_needs_an_owner(tmp_path):
    path = tmp_path / "known_drift.toml"
    path.write_text(
        '[[model]]\ntable = "role"\ncolumn = "title"\nkind = "nullability"\ndetail = "x"\n', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="owner"):
        load_known(path)


def test_an_unknown_kind_is_refused(tmp_path):
    path = tmp_path / "known_drift.toml"
    path.write_text('[[model]]\ntable = "role"\nkind = "renamed"\nowner = "people"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="renamed"):
        load_known(path)


def test_the_recorded_drift_loads_and_every_entry_has_an_owner():
    known = load_known()

    assert known
    assert all(known.values())
