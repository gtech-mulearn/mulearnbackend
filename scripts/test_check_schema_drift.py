"""
Tests for the schema/model drift check.

Standalone under pytest — no Django, no database:

    pytest scripts/test_check_schema_drift.py
"""

from check_schema_drift import (
    columns_from_models,
    columns_from_sql,
    find_drift,
    inherited_tables_from_models,
    main,
)

# Trimmed from db-scripts/latest.sql — the real `user` table.
USER_SQL = """
CREATE TABLE `user` (
  `id` varchar(36) NOT NULL,
  `full_name` varchar(150) NOT NULL,
  `email` varchar(200) NOT NULL,
  `district_id` varchar(36) DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted_by` varchar(36) DEFAULT NULL,
  `suspended_by` varchar(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  KEY `fk_user_ref_district_id` (`district_id`),
  CONSTRAINT `fk_user_ref_deleted_by` FOREIGN KEY (`deleted_by`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def test_parses_columns_and_ignores_keys_and_constraints():
    tables = columns_from_sql(USER_SQL)

    assert tables["user"] == {
        "id",
        "full_name",
        "email",
        "district_id",
        "deleted_at",
        "deleted_by",
        "suspended_by",
    }


def test_detects_column_present_in_sql_but_missing_from_model():
    """
    The F19 case, exactly: `deleted_at` and `deleted_by` were added by DDL and
    never mirrored into either ORM, because agent.md Step 4 is manual.
    """
    model_source = """
class User(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True, max_length=200)
    district = models.ForeignKey("District", on_delete=models.CASCADE)
    suspended_by = models.ForeignKey("self", db_column="suspended_by")

    class Meta:
        managed = False
        db_table = 'user'
"""
    drift = find_drift(columns_from_sql(USER_SQL), columns_from_models(model_source))

    assert drift == [
        ("user", "deleted_at", "in schema, not declared in model"),
        ("user", "deleted_by", "in schema, not declared in model"),
    ]


def test_foreign_key_maps_to_column_with_id_suffix():
    """`district = ForeignKey(...)` is the column `district_id`, not `district`."""
    model_source = """
class User(models.Model):
    district = models.ForeignKey("District", on_delete=models.CASCADE)

    class Meta:
        db_table = 'user'
"""
    assert columns_from_models(model_source)["user"] == {"district_id"}


def test_db_column_overrides_the_field_name():
    model_source = """
class User(models.Model):
    suspended_by = models.ForeignKey("self", db_column="suspended_by")

    class Meta:
        db_table = 'user'
"""
    assert columns_from_models(model_source)["user"] == {"suspended_by"}


def test_detects_column_declared_in_model_but_absent_from_schema():
    """The reverse drift: a model field with no backing column crashes at runtime."""
    model_source = """
class User(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(max_length=200)
    district = models.ForeignKey("District", on_delete=models.CASCADE)
    deleted_at = models.DateTimeField(null=True)
    deleted_by = models.CharField(max_length=36, null=True)
    suspended_by = models.ForeignKey("self", db_column="suspended_by")
    invented_field = models.CharField(max_length=10)

    class Meta:
        db_table = 'user'
"""
    drift = find_drift(columns_from_sql(USER_SQL), columns_from_models(model_source))

    assert drift == [("user", "invented_field", "declared in model, not in schema")]


def test_no_drift_when_model_matches_schema():
    model_source = """
class User(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(max_length=200)
    district = models.ForeignKey("District", on_delete=models.CASCADE)
    deleted_at = models.DateTimeField(null=True)
    deleted_by = models.CharField(max_length=36, null=True)
    suspended_by = models.ForeignKey("self", db_column="suspended_by")

    class Meta:
        db_table = 'user'
"""
    assert find_drift(columns_from_sql(USER_SQL), columns_from_models(model_source)) == []


def test_tables_without_a_model_are_ignored():
    """
    Each service mirrors only part of the schema. A table with no model in the
    files being checked is not drift — flagging it would make the check noise.
    """
    sql = USER_SQL + """
CREATE TABLE `some_other_table` (
  `id` varchar(36) NOT NULL
) ENGINE=InnoDB;
"""
    model_source = """
class Unrelated(models.Model):
    id = models.CharField(primary_key=True, max_length=36)

    class Meta:
        db_table = 'unrelated'
"""
    drift = find_drift(columns_from_sql(sql), columns_from_models(model_source))

    assert all(table != "some_other_table" for table, _, _ in drift)


def test_commented_out_fields_are_not_counted_as_declared():
    """
    authserver's User has `# district = models.ForeignKey(...)` commented out.
    A comment is not a declaration — treating it as one would hide real drift.
    """
    model_source = """
class User(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    # district = models.ForeignKey("District", on_delete=models.CASCADE)

    class Meta:
        db_table = 'user'
"""
    assert columns_from_models(model_source)["user"] == {"id"}


def test_parses_the_plain_style_used_by_latest_sql():
    """
    db-scripts/latest.sql is NOT in MySQL-dump style: no backticks, the opening
    paren on its own line, and `);` rather than `) ENGINE=...` as terminator.
    mulearnbackend/schema.sql IS dump style. Both must parse.
    """
    sql = """
CREATE TABLE user
(
    id             VARCHAR(36) PRIMARY KEY NOT NULL,
    muid           VARCHAR(100) UNIQUE KEY NOT NULL,
    deleted_at     DATETIME,
    CONSTRAINT fk_user_ref_deleted_by FOREIGN KEY (deleted_by) REFERENCES user (id)
);

CREATE TABLE wallet
(
    id      VARCHAR(36) PRIMARY KEY NOT NULL,
    karma   INT
);
"""
    tables = columns_from_sql(sql)

    assert tables["user"] == {"id", "muid", "deleted_at"}
    # The bug this catches: without balanced-paren scanning, `user` swallowed
    # every following table's columns because it kept looking for `) ENGINE`.
    assert tables["wallet"] == {"id", "karma"}


def test_nested_parens_in_column_types_do_not_end_the_table():
    sql = """
CREATE TABLE thing
(
    id       VARCHAR(36) NOT NULL,
    amount   DECIMAL(10, 2) DEFAULT 0.00,
    label    ENUM('a', 'b') NOT NULL
);
"""
    assert columns_from_sql(sql)["thing"] == {"id", "amount", "label"}


def test_semicolon_inside_a_string_literal_does_not_end_the_statement():
    """
    Real case from latest.sql: a COMMENT string containing a semicolon
    truncated the ALTER body, so every column after it read as missing from
    the schema and produced a false 'declared in model, not in schema'.
    Only surfaced by running against the real file.
    """
    sql = """
CREATE TABLE user_mentor
(
    id VARCHAR(36) PRIMARY KEY NOT NULL
);

ALTER TABLE user_mentor
    ADD COLUMN preferred_ig_ids JSON DEFAULT NULL COMMENT 'UUIDs; auto-creates links',
    ADD COLUMN org_id VARCHAR(36) DEFAULT NULL,
    ADD KEY fk_user_mentor_ref_org_id (org_id);
"""
    assert columns_from_sql(sql)["user_mentor"] == {
        "id",
        "preferred_ig_ids",
        "org_id",
    }


def test_add_column_keyword_is_optional():
    """MySQL permits `ADD <name> <type>` without the COLUMN keyword."""
    sql = """
CREATE TABLE thing
(
    id VARCHAR(36) PRIMARY KEY NOT NULL
);

ALTER TABLE thing ADD nickname VARCHAR(50);
"""
    assert columns_from_sql(sql)["thing"] == {"id", "nickname"}


def test_alter_table_add_column_is_applied_to_the_table():
    """
    latest.sql appends each alter script verbatim (agent.md Step 3), so ALTER
    statements must be honoured or every post-baseline column reads as missing.
    """
    sql = """
CREATE TABLE `user` (
  `id` varchar(36) NOT NULL
) ENGINE=InnoDB;

ALTER TABLE user
    ADD COLUMN deleted_at DATETIME,
    ADD COLUMN deleted_by VARCHAR(36);
"""
    assert columns_from_sql(sql)["user"] == {"id", "deleted_at", "deleted_by"}


def test_multiline_foreign_key_clauses_are_not_columns():
    """
    A wrapped FK definition puts REFERENCES and ON at the start of their own
    lines. Both are SQL keywords, not columns — but _NOT_A_COLUMN only listed
    the keywords that begin a constraint, so these leaked through and showed up
    as `launchpad_job_applications.ON` / `.REFERENCES` against the real
    db-scripts/latest.sql.
    """
    sql = """
CREATE TABLE job_application (
    id VARCHAR(36) PRIMARY KEY,
    job_id VARCHAR(36) NOT NULL,

    CONSTRAINT fk_job FOREIGN KEY (job_id)
        REFERENCES jobs(id)
        ON DELETE CASCADE
);
"""
    assert columns_from_sql(sql)["job_application"] == {"id", "job_id"}


# A model declaring only three of `user`'s columns, so the remaining schema
# columns show up as drift that the baseline file is then asked to absorb.
MODEL_SRC = """from django.db import models


class User(models.Model):
    id = models.CharField(max_length=36)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(max_length=200)

    class Meta:
        db_table = 'user'
"""


class TestIgnoreFile:
    """
    A large pre-existing backlog of divergences is accepted for now (see the
    baseline files). CI must block NEW drift without failing on that backlog,
    and dozens of entries on a command line is not usable — hence a file.
    """

    def _write(self, tmp_path, name, text):
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def _model(self, tmp_path):
        return self._write(tmp_path, "m.py", MODEL_SRC)

    def test_entries_in_the_file_are_ignored(self, tmp_path):
        sql = self._write(tmp_path, "s.sql", USER_SQL)
        ignore = self._write(
            tmp_path,
            "ignore.txt",
            "user.district_id\nuser.deleted_at\nuser.deleted_by\nuser.suspended_by\n",
        )
        assert (
            main(
                [
                    "--sql", sql,
                    "--models", self._model(tmp_path),
                    "--ignore-file", ignore,
                ]
            )
            == 0
        )

    def test_blank_lines_and_comments_are_skipped(self, tmp_path):
        sql = self._write(tmp_path, "s.sql", USER_SQL)
        ignore = self._write(
            tmp_path,
            "ignore.txt",
            "# Accepted backlog\n"
            "\n"
            "user.district_id   # profile field\n"
            "user.deleted_at\n"
            "user.deleted_by\n"
            "\n"
            "user.suspended_by\n",
        )
        assert (
            main(
                [
                    "--sql", sql,
                    "--models", self._model(tmp_path),
                    "--ignore-file", ignore,
                ]
            )
            == 0
        )

    def test_a_divergence_not_in_the_file_still_fails(self, tmp_path):
        # This is the whole point: the baseline must not become a blanket pass.
        sql = self._write(tmp_path, "s.sql", USER_SQL)
        ignore = self._write(tmp_path, "ignore.txt", "user.district_id\n")
        assert (
            main(
                [
                    "--sql", sql,
                    "--models", self._model(tmp_path),
                    "--ignore-file", ignore,
                ]
            )
            == 1
        )

    def test_a_missing_ignore_file_is_an_invocation_error_not_a_pass(self, tmp_path):
        # Silently continuing when the baseline is missing would disable the
        # gate the first time someone renames the file.
        sql = self._write(tmp_path, "s.sql", USER_SQL)
        missing = str(tmp_path / "nope.txt")
        assert (
            main(
                [
                    "--sql", sql,
                    "--models", self._model(tmp_path),
                    "--ignore-file", missing,
                ]
            )
            == 2
        )

    def test_ignore_file_and_ignore_flag_combine(self, tmp_path):
        sql = self._write(tmp_path, "s.sql", USER_SQL)
        ignore = self._write(
            tmp_path, "ignore.txt", "user.district_id\nuser.deleted_at\n"
        )
        assert (
            main(
                [
                    "--sql", sql,
                    "--models", self._model(tmp_path),
                    "--ignore-file", ignore,
                    "--ignore", "user.deleted_by", "user.suspended_by",
                ]
            )
            == 0
        )


INHERITED_SQL = """
CREATE TABLE `oauth2_provider_application` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `client_id` varchar(255) NOT NULL,
  `client_secret` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

INHERITED_MODEL = """
from oauth2_provider.models import AbstractApplication


class OAuthApplication(AbstractApplication):
    class Meta(AbstractApplication.Meta):
        managed = False
        db_table = 'oauth2_provider_application'
"""

PARTIAL_MODEL = """
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models


class Identity(AbstractBaseUser):
    id = models.CharField(primary_key=True, max_length=36)
    email = models.EmailField(unique=True, max_length=200)

    class Meta:
        managed = False
        db_table = 'identity'
"""

IDENTITY_SQL = """
CREATE TABLE `identity` (
  `id` varchar(36) NOT NULL,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `email` varchar(200) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


class TestInheritedFields:
    """
    A model that inherits its fields from a base class in site-packages cannot
    be read by static analysis: the ClassDef body has no field assignments at
    all. Reporting every inherited column as "missing from the model" is a
    false positive, and baselining them would switch the gate off for the
    OAuth tables specifically.

    So for such a model the checker only reports the DANGEROUS direction --
    a column declared in the model but absent from the schema, which fails at
    query time in production. Columns present in the schema but not visible in
    the model are assumed inherited and left alone.
    """

    def test_model_with_no_own_fields_reports_no_false_drift(self):
        sql = columns_from_sql(INHERITED_SQL)
        models = columns_from_models(INHERITED_MODEL)
        inherited = inherited_tables_from_models(INHERITED_MODEL)
        assert find_drift(sql, models, inherited) == []

    def test_partially_inherited_model_ignores_inherited_columns(self):
        # password / last_login come from AbstractBaseUser and are invisible here.
        sql = columns_from_sql(IDENTITY_SQL)
        models = columns_from_models(PARTIAL_MODEL)
        inherited = inherited_tables_from_models(PARTIAL_MODEL)
        assert find_drift(sql, models, inherited) == []

    def test_a_model_field_with_no_column_is_STILL_reported(self):
        # The direction that matters: the ORM references a column the schema
        # does not have. This must survive the inheritance allowance.
        model = PARTIAL_MODEL.replace(
            "    email = models.EmailField(unique=True, max_length=200)",
            "    email = models.EmailField(unique=True, max_length=200)\n"
            "    nickname = models.CharField(max_length=50)",
        )
        drift = find_drift(
            columns_from_sql(IDENTITY_SQL),
            columns_from_models(model),
            inherited_tables_from_models(model),
        )
        assert ("identity", "nickname", "declared in model, not in schema") in drift

    def test_plain_model_still_reports_both_directions(self):
        # No inheritance -> unchanged behaviour, both directions reported.
        plain = """
from django.db import models


class Thing(models.Model):
    id = models.CharField(max_length=36)

    class Meta:
        db_table = 'thing'
"""
        sql = "CREATE TABLE `thing` (\n  `id` varchar(36) NOT NULL,\n  `name` varchar(10) NOT NULL\n);"
        drift = find_drift(columns_from_sql(sql), columns_from_models(plain))
        assert ("thing", "name", "in schema, not declared in model") in drift
