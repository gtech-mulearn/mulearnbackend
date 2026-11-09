"""The models must mirror db-scripts alter-1.92 column for column."""
import pathlib
import re

import pytest

from db.integrations import IntegrationAccountEvent, IntegrationAccountLink

ALTER = pathlib.Path(__file__).resolve().parents[5] / "db-scripts" / "alter" / "alter-1.92.sql"


def sql_columns(table):
    if not ALTER.exists():
        pytest.skip("db-scripts is not checked out next to mulearnbackend")
    block = re.search(rf"CREATE TABLE IF NOT EXISTS `{table}`\s*\((.*?)\n\)[^;]*;", ALTER.read_text(encoding="utf-8"), re.S)
    return {match for match in re.findall(r"^\s*`(\w+)`\s+[A-Z]", block.group(1), re.M)}


@pytest.mark.parametrize("model", [IntegrationAccountLink, IntegrationAccountEvent])
def test_model_columns_match_the_sql(model):
    assert {field.column for field in model._meta.concrete_fields} == sql_columns(model._meta.db_table)


def test_models_are_unmanaged():
    assert not IntegrationAccountLink._meta.managed
    assert not IntegrationAccountEvent._meta.managed
