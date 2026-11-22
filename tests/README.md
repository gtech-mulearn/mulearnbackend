# Tests

Run tests with `scripts/test.sh` (or `scripts\test.ps1`), never with `pytest` directly. Setup and troubleshooting are in [DEVELOPMENT.md](../DEVELOPMENT.md#run-the-tests).

## The two tiers

| Tier | Command | Database |
|---|---|---|
| Unit | `scripts/test.sh tests/ building_blocks/` | In-memory SQLite, with none of the schema's tables |
| MySQL | `scripts/test.sh --mysql tests/ building_blocks/` | `test_mulearn`, loaded from `schema/latest.sql` |

CI runs the unit tier in `ci / unit`, and the MySQL tier on MySQL 8.0 and 8.4 in `ci / mysql`.

## The rule

**A test that reads or writes a schema table runs on the MySQL tier and carries both markers:**

```python
pytestmark = [pytest.mark.mysql, pytest.mark.django_db]
```

- **`--mysql` runs only tests marked `mysql`.** The unit tier runs every other test.
- **The MySQL tier uses `test_mulearn` as it was loaded.** pytest-django would create an empty `test_test_mulearn`, because every model is `managed = False` and there are no migrations. The root `conftest.py` turns that off.
- **Use `transaction=True` only when a test needs rows committed across connections,** such as a concurrency test.
  - Its rows stay committed, so the test creates every row it needs and never relies on rows another test left.
  - The system user is put back before each `mysql` test and when the session ends.

## What's here

- `mysql/`: checks of the MySQL tier itself.
- `architecture/`: the import contracts and the module graph.
- `legacy_baseline.txt`: the legacy tests that fail today, for `scripts/legacy_ratchet.py`. It only shrinks.
