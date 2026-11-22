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
- `schema/`: parity between the models and the loaded schema. Known drift is in `schema/known_drift.toml`, which only shrinks.
- `architecture/`: the import contracts and the module graph.
- `characterization/`: tests that pin a legacy route's response, status and query count before it moves. Its `conftest.py` has the fixtures (`make_user`, `api_client`, `assert_envelope`, `golden`). Run with `--update-golden` to rewrite the golden files, then review the diff.
- `legacy_baseline.txt`: the legacy tests that fail today, for `scripts/legacy_ratchet.py`. It only shrinks.
