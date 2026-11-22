"""Unmanaged models match the loaded schema's tables (issue 0053). Reads information_schema only."""

from itertools import groupby

import pytest
from django.db import connection

from tests.schema.enum_parity import KNOWN_DRIFT, unexpected_and_fixed
from tests.schema.model_parity import compare_all, load_known, read_schema, unmanaged_models

pytestmark = [pytest.mark.mysql, pytest.mark.django_db]


def report(title, differences):
    lines = [title]
    for kind, group in groupby(sorted(differences, key=lambda d: (d.kind, d)), key=lambda d: d.kind):
        lines.append(f"  {kind}:")
        lines += [f"    {difference.describe()}" for difference in group]
    return lines


def test_models_match_the_tables_they_map():
    unexpected, fixed = unexpected_and_fixed(compare_all(read_schema(connection)), load_known())

    lines = []
    if unexpected:
        lines += report(
            f"Model/schema drift that isn't recorded in {KNOWN_DRIFT.name}. Fix the model (or the schema, through"
            " a db-scripts alter), or record it as a [[model]] entry with an owner:",
            unexpected,
        )
    if fixed:
        lines += report(f"Recorded drift that's fixed. Delete these [[model]] entries from {KNOWN_DRIFT.name}:", fixed)
    assert not lines, "\n".join(lines)


def test_every_unmanaged_model_is_compared():
    assert len(unmanaged_models()) > 100
