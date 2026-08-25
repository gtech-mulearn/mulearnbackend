#!/usr/bin/env python3
"""
Schema/model drift check.

Why this exists
---------------
`db-scripts/agent.md` Step 4 asks contributors to mirror every schema change
into the Django models by hand, and notes that all models are `managed = False`.
Nothing enforces it: no migration, no test, no CI gate. So a column can be added
by DDL and simply never appear in the ORM.

That is not theoretical. `deleted_at` and `deleted_by` were added to `user` and
are declared in *neither* `mulearnbackend/db/user.py` nor
`authserver/muauth/models.py` (audit finding F19), and four further columns are
missing from one mirror or the other. Deleting a user by setting `deleted_at`
would appear to work while both services continued to authenticate them,
because neither `ActiveUserManager` can filter on a column it does not know
about.

This script turns that manual step into an enforced one.

Deliberately dependency-free: no Django, no database, no settings. It parses
SQL with regex and models with `ast`, so it runs in CI in under a second and
cannot be broken by an import cycle or a missing env var.

Usage
-----
    python scripts/check_schema_drift.py \
        --sql ../db-scripts/latest.sql \
        --models db/*.py

    python scripts/check_schema_drift.py \
        --sql ../db-scripts/latest.sql \
        --models ../authserver/muauth/models.py

Exit codes: 0 = no drift, 1 = drift found, 2 = bad invocation.
"""

import argparse
import ast
import glob
import re
import sys

# Two dialects are in play and both must parse:
#   db-scripts/latest.sql  — plain: no backticks, `(` on its own line, `);` end
#   mulearnbackend/schema.sql — MySQL dump: backticked, `) ENGINE=...` end
# So: locate `CREATE TABLE <name>` then scan with balanced parens rather than
# regex-matching a terminator. Matching on `) ENGINE` silently made one table
# swallow every following table's columns in the plain dialect — 63 false
# divergences on the real file, which is exactly how a check gets disabled.
_CREATE_HEAD = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(?P<table>\w+)`?\s*\(",
    re.IGNORECASE,
)
# A column line starts with an identifier (optionally backticked) followed by
# whitespace and a type token.
_COLUMN = re.compile(r"^\s*`?(?P<name>\w+)`?\s+\w", re.MULTILINE)


def _table_body(sql_text, open_paren_index):
    """
    Text between the table's opening paren and its matching close.

    Paren counting, so `DECIMAL(10, 2)` and `ENUM('a','b')` inside a column
    definition do not terminate the table early.
    """
    depth = 0
    for index in range(open_paren_index, len(sql_text)):
        char = sql_text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return sql_text[open_paren_index + 1:index]
    return sql_text[open_paren_index + 1:]
# latest.sql appends every alter script verbatim, so post-baseline columns
# arrive as ALTER statements rather than inside CREATE TABLE.
_ALTER_HEAD = re.compile(r"ALTER\s+TABLE\s+`?(?P<table>\w+)`?\s", re.IGNORECASE)
# `COLUMN` is optional in MySQL: `ADD nickname VARCHAR(50)` is valid.
# The negative lookahead keeps `ADD KEY` / `ADD CONSTRAINT` / `ADD INDEX`
# from being read as columns.
_ADD_COLUMN = re.compile(
    r"ADD\s+(?:COLUMN\s+)?(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?!KEY\b|CONSTRAINT\b|INDEX\b|PRIMARY\b|UNIQUE\b|FOREIGN\b|FULLTEXT\b|SPATIAL\b|CHECK\b)"
    r"`?(?P<name>\w+)`?",
    re.IGNORECASE,
)
_DROP_COLUMN = re.compile(
    r"DROP\s+COLUMN\s+(?:IF\s+EXISTS\s+)?`?(?P<name>\w+)`?", re.IGNORECASE
)


def _statement_end(sql_text, start):
    """
    Index of the `;` ending the statement at `start`, ignoring semicolons
    inside quoted strings.

    latest.sql contains `COMMENT 'JSON list of IG UUIDs the mentor prefers;
    auto-creates UserIgLink on verification'`. Terminating on the first raw
    `;` truncated that ALTER and made every column after it read as absent
    from the schema — a false positive on real data.
    """
    quote = None
    index = start
    while index < len(sql_text):
        char = sql_text[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in ("'", '"', "`"):
            quote = char
        elif char == ";":
            return index
        index += 1
    return len(sql_text)

# Lines inside CREATE TABLE that define constraints rather than columns.
#
# REFERENCES and ON are here because a wrapped foreign-key definition puts them
# at the start of a continuation line:
#
#     CONSTRAINT fk_job FOREIGN KEY (job_id)
#         REFERENCES jobs(id)
#         ON DELETE CASCADE
#
# Listing only the keywords that *begin* a constraint let those two through,
# which reported `launchpad_job_applications.ON` and `.REFERENCES` as real
# columns against db-scripts/latest.sql.
_NOT_A_COLUMN = re.compile(
    r"^\s*(PRIMARY|UNIQUE|KEY|INDEX|CONSTRAINT|FOREIGN|FULLTEXT|SPATIAL|CHECK"
    r"|REFERENCES|ON)\b",
    re.IGNORECASE | re.MULTILINE,
)

# Django field classes that do not correspond to a column on this table.
_NON_COLUMN_FIELDS = {"ManyToManyField", "OneToOneRel", "ForeignObjectRel"}
# Class attributes that are managers or config, not fields.
_NON_FIELD_ASSIGNMENTS = {"objects", "every", "USERNAME_FIELD", "REQUIRED_FIELDS"}


def columns_from_sql(sql_text):
    """Map table name -> set of column names, honouring CREATE and ALTER."""
    tables = {}

    for match in _CREATE_HEAD.finditer(sql_text):
        body = _table_body(sql_text, match.end() - 1)
        columns = {
            m.group("name")
            for line in body.splitlines()
            if not _NOT_A_COLUMN.match(line)
            for m in _COLUMN.finditer(line)
        }
        # A table may be recreated later in the file; last definition wins.
        tables[match.group("table")] = columns

    for match in _ALTER_HEAD.finditer(sql_text):
        table = match.group("table")
        if table not in tables:
            # An ALTER on a table whose CREATE we never saw. Skip rather than
            # invent a partial table that would report spurious drift.
            continue
        body = sql_text[match.end():_statement_end(sql_text, match.end())]
        tables[table] |= {m.group("name") for m in _ADD_COLUMN.finditer(body)}
        tables[table] -= {m.group("name") for m in _DROP_COLUMN.finditer(body)}

    return tables


def _db_table_of(class_node):
    """The Meta.db_table value for a model class, or None."""
    for node in class_node.body:
        if isinstance(node, ast.ClassDef) and node.name == "Meta":
            for meta_node in node.body:
                if (
                    isinstance(meta_node, ast.Assign)
                    and any(
                        isinstance(t, ast.Name) and t.id == "db_table"
                        for t in meta_node.targets
                    )
                    and isinstance(meta_node.value, ast.Constant)
                ):
                    return meta_node.value.value
    return None


def _column_of(field_name, call_node):
    """
    The column a field maps to.

    ForeignKey/OneToOneField get an `_id` suffix unless `db_column` overrides
    it. Getting this wrong in either direction produces false drift, which is
    worse than no check at all — a noisy check gets disabled.
    """
    field_type = ""
    if isinstance(call_node.func, ast.Attribute):
        field_type = call_node.func.attr
    elif isinstance(call_node.func, ast.Name):
        field_type = call_node.func.id

    if field_type in _NON_COLUMN_FIELDS:
        return None

    for keyword in call_node.keywords:
        if keyword.arg == "db_column" and isinstance(keyword.value, ast.Constant):
            return keyword.value.value

    if field_type in {"ForeignKey", "OneToOneField"}:
        return f"{field_name}_id"

    return field_name


def columns_from_models(python_source):
    """
    Map db_table -> set of column names declared in Django models.

    Uses `ast`, so commented-out fields are invisible — which is correct:
    `authserver`'s `User` has a commented-out `district` FK, and counting it
    as declared would mask real drift.
    """
    tree = ast.parse(python_source)
    tables = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        table = _db_table_of(node)
        if not table:
            continue

        columns = set()
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign) or not isinstance(stmt.value, ast.Call):
                continue
            for target in stmt.targets:
                if not isinstance(target, ast.Name):
                    continue
                if target.id in _NON_FIELD_ASSIGNMENTS:
                    continue
                column = _column_of(target.id, stmt.value)
                if column:
                    columns.add(column)

        tables[table] = columns

    return tables


def inherited_tables_from_models(python_source):
    """
    db_table names whose model inherits fields from a base class this script
    cannot see.

    A model like `class OAuthApplication(AbstractApplication)` declares no
    fields in its own body — every column comes from a base class in
    site-packages. `ast` cannot follow that, so the columns are invisible here
    and would otherwise be reported as missing from the model. Identifying
    those tables lets find_drift suppress that one direction, rather than
    emitting dozens of false positives or forcing the OAuth tables into an
    ignore file, which would switch the gate off exactly where it matters most.

    A base of `models.Model` (or bare `Model`) is the ordinary case and does
    NOT count: those models declare their own fields.
    """
    tree = ast.parse(python_source)
    inherited = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        table = _db_table_of(node)
        if not table:
            continue
        for base in node.bases:
            if isinstance(base, ast.Attribute):
                name = base.attr
            elif isinstance(base, ast.Name):
                name = base.id
            else:
                continue
            if name != "Model":
                inherited.add(table)
                break

    return inherited


def find_drift(sql_tables, model_tables, inherited_tables=frozenset()):
    """
    Divergences between schema and models, as (table, column, direction).

    Only tables present in BOTH are compared: each service mirrors part of the
    schema, so a table with no model here is not drift.

    For a table in `inherited_tables`, only the dangerous direction is reported.
    A column the model declares but the schema lacks fails at QUERY time in
    production, so it is always reported. A column in the schema that the model
    does not appear to declare is assumed inherited from an unreadable base
    class rather than missing.
    """
    drift = []

    for table in sorted(set(sql_tables) & set(model_tables)):
        sql_columns = sql_tables[table]
        model_columns = model_tables[table]

        if table not in inherited_tables:
            for column in sorted(sql_columns - model_columns):
                drift.append((table, column, "in schema, not declared in model"))
        for column in sorted(model_columns - sql_columns):
            drift.append((table, column, "declared in model, not in schema"))

    return drift


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sql", required=True, help="Path to latest.sql")
    parser.add_argument(
        "--models", required=True, nargs="+", help="Model files or globs"
    )
    parser.add_argument(
        "--ignore",
        nargs="*",
        default=[],
        metavar="TABLE.COLUMN",
        help="Known, accepted divergences (e.g. user.deleted_at)",
    )
    parser.add_argument(
        "--ignore-file",
        metavar="PATH",
        help=(
            "File of accepted divergences, one TABLE.COLUMN per line. "
            "Blank lines and #-comments are skipped. A missing file is an "
            "invocation error, not a pass — otherwise renaming the baseline "
            "would silently disable the gate."
        ),
    )
    args = parser.parse_args(argv)

    try:
        with open(args.sql, encoding="utf-8", errors="replace") as handle:
            sql_tables = columns_from_sql(handle.read())
    except OSError as exc:
        print(f"error: could not read {args.sql}: {exc}", file=sys.stderr)
        return 2

    paths = [p for pattern in args.models for p in glob.glob(pattern)]
    if not paths:
        print(f"error: no model files matched {args.models}", file=sys.stderr)
        return 2

    model_tables = {}
    inherited_tables = set()
    for path in paths:
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                source = handle.read()
            model_tables.update(columns_from_models(source))
            inherited_tables.update(inherited_tables_from_models(source))
        except SyntaxError as exc:
            print(f"error: could not parse {path}: {exc}", file=sys.stderr)
            return 2

    ignored = set(args.ignore)
    if args.ignore_file:
        try:
            with open(args.ignore_file, encoding="utf-8") as handle:
                for line in handle:
                    entry = line.split("#", 1)[0].strip()
                    if entry:
                        ignored.add(entry)
        except OSError as exc:
            print(
                f"error: could not read {args.ignore_file}: {exc}", file=sys.stderr
            )
            return 2

    drift = [
        entry for entry in find_drift(sql_tables, model_tables, inherited_tables)
        if f"{entry[0]}.{entry[1]}" not in ignored
    ]

    partial = sorted(inherited_tables & set(sql_tables) & set(model_tables))

    if not drift:
        print(
            f"No drift. Compared {len(set(sql_tables) & set(model_tables))} tables "
            f"across {len(paths)} model file(s)."
        )
        if partial:
            # Say so out loud. A silently-relaxed check is how a gate stops
            # meaning anything.
            print()
            print(
                f"{len(partial)} table(s) checked one-way only, because the model "
                f"inherits its fields from a base class this script cannot read:"
            )
            for table in partial:
                print(f"  {table}")
            print(
                "For these, a model field with no column is still reported; a "
                "column not visible in the model is assumed inherited."
            )
        return 0

    print(f"Schema/model drift — {len(drift)} divergence(s):\n")
    for table, column, direction in drift:
        print(f"  {table}.{column}: {direction}")
    print(
        "\nSchema changes must be mirrored into the Django models "
        "(db-scripts/agent.md, Step 4).\n"
        "If a divergence is intentional, pass it via --ignore."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
