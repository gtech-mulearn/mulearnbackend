
SELECT VERSION()  AS mysql_version;
SELECT DATABASE() AS target_schema;

-- ============================================================================
-- M1. CORE EVENT TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS event
(
    id                    VARCHAR(36)   NOT NULL,

    -- Content
    title                 VARCHAR(200)  NOT NULL,
    slug                  VARCHAR(220)  NOT NULL,
    description           TEXT          NOT NULL,
    cover_image           VARCHAR(500)  DEFAULT NULL,
    banner_image          VARCHAR(500)  DEFAULT NULL,

    -- Classification
    event_type            ENUM(
                              'workshop', 'webinar', 'hackathon',
                              'meetup', 'competition', 'social_gathering', 'other'
                          )             NOT NULL DEFAULT 'other',

    -- Lifecycle
    status                ENUM(
                              'draft',
                              'pending_campus_approval',
                              'pending_approval',
                              'pending_mentor_approval',
                              'published',
                              'ongoing',
                              'completed',
                              'cancelled'
                          )             NOT NULL DEFAULT 'draft',

    -- Dates
    start_datetime        DATETIME      NOT NULL,
    end_datetime          DATETIME      NOT NULL,

    -- External registration
    registration_url      VARCHAR(500)  DEFAULT NULL,
    registration_deadline DATETIME      DEFAULT NULL,

    -- Karma eligibility gate
    min_karma             BIGINT UNSIGNED DEFAULT NULL,

    -- Flags
    is_collaboration      BOOLEAN       NOT NULL DEFAULT FALSE,
    is_featured           BOOLEAN       NOT NULL DEFAULT FALSE,

    -- Denormalised counter (kept in sync by M11 triggers)
    interest_count        INT UNSIGNED  NOT NULL DEFAULT 0,

    -- Audit
    created_by            VARCHAR(36)   NOT NULL,
    created_at            DATETIME      NOT NULL,
    updated_by            VARCHAR(36)   NOT NULL,
    updated_at            DATETIME      NOT NULL,
    deleted_at            DATETIME      DEFAULT NULL,
    deleted_by            VARCHAR(36)   DEFAULT NULL,

    PRIMARY KEY (id),

    CONSTRAINT uq_event_slug       UNIQUE  (slug),
    CONSTRAINT chk_event_dates     CHECK   (end_datetime > start_datetime),
    CONSTRAINT chk_event_min_karma CHECK   (min_karma IS NULL OR min_karma >= 0),

    CONSTRAINT fk_event_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE RESTRICT,
    CONSTRAINT fk_event_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE RESTRICT,
    CONSTRAINT fk_event_deleted_by FOREIGN KEY (deleted_by) REFERENCES user (id) ON DELETE SET NULL
);


-- ============================================================================
-- M2. EVENT TAGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_tag
(
    id         VARCHAR(36)  NOT NULL,
    name       VARCHAR(50)  NOT NULL,
    created_at DATETIME     NOT NULL,

    PRIMARY KEY (id),
    CONSTRAINT uq_event_tag_name UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS event_tag_link
(
    id         VARCHAR(36)  NOT NULL,
    event_id   VARCHAR(36)  NOT NULL,
    tag_id     VARCHAR(36)  NOT NULL,
    created_at DATETIME     NOT NULL,

    PRIMARY KEY (id),

    CONSTRAINT uq_event_tag_link UNIQUE (event_id, tag_id),

    CONSTRAINT fk_etl_event FOREIGN KEY (event_id) REFERENCES event     (id) ON DELETE CASCADE,
    CONSTRAINT fk_etl_tag   FOREIGN KEY (tag_id)   REFERENCES event_tag (id) ON DELETE CASCADE
);


-- ============================================================================
-- M3. EVENT VENUE (1-to-1 with event)
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_venue
(
    id          VARCHAR(36)  NOT NULL,
    event_id    VARCHAR(36)  NOT NULL,
    venue_type  ENUM('physical', 'online', 'hybrid') NOT NULL,

    -- Physical / hybrid
    address     VARCHAR(300) DEFAULT NULL,
    city        VARCHAR(100) DEFAULT NULL,
    maps_url    VARCHAR(500) DEFAULT NULL,

    -- Online / hybrid
    online_link VARCHAR(500) DEFAULT NULL,
    platform    VARCHAR(100) DEFAULT NULL,

    created_at  DATETIME     NOT NULL,
    updated_at  DATETIME     NOT NULL,

    PRIMARY KEY (id),
    CONSTRAINT uq_event_venue_event UNIQUE (event_id),

    CONSTRAINT fk_event_venue_event FOREIGN KEY (event_id) REFERENCES event (id) ON DELETE CASCADE
);


-- ============================================================================
-- M4. EVENT SCOPE & TARGETING (1-to-1 with event)
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_scope
(
    id               VARCHAR(36)  NOT NULL,
    event_id         VARCHAR(36)  NOT NULL,
    scope            ENUM('global', 'campus', 'ig', 'campus_ig') NOT NULL DEFAULT 'global',

    target_org_id    VARCHAR(36)  DEFAULT NULL,
    target_ig_id     VARCHAR(36)  DEFAULT NULL,
    target_ci_org_id VARCHAR(36)  DEFAULT NULL,
    target_ci_ig_id  VARCHAR(36)  DEFAULT NULL,

    created_at       DATETIME     NOT NULL,
    updated_at       DATETIME     NOT NULL,

    PRIMARY KEY (id),
    CONSTRAINT uq_event_scope_event UNIQUE (event_id),

    CONSTRAINT fk_es_event  FOREIGN KEY (event_id)         REFERENCES event          (id) ON DELETE CASCADE,
    CONSTRAINT fk_es_org    FOREIGN KEY (target_org_id)    REFERENCES organization   (id) ON DELETE SET NULL,
    CONSTRAINT fk_es_ig     FOREIGN KEY (target_ig_id)     REFERENCES interest_group (id) ON DELETE SET NULL,
    CONSTRAINT fk_es_ci_org FOREIGN KEY (target_ci_org_id) REFERENCES organization   (id) ON DELETE SET NULL,
    CONSTRAINT fk_es_ci_ig  FOREIGN KEY (target_ci_ig_id)  REFERENCES interest_group (id) ON DELETE SET NULL
);


-- ============================================================================
-- M5. EVENT ORGANISER (1-to-1 with event)
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_organiser
(
    id             VARCHAR(36)  NOT NULL,
    event_id       VARCHAR(36)  NOT NULL,
    organiser_type ENUM('global_ig', 'campus_ig', 'campus', 'company', 'admin') NOT NULL,

    ig_id          VARCHAR(36)  DEFAULT NULL,
    org_id         VARCHAR(36)  DEFAULT NULL,
    ci_org_id      VARCHAR(36)  DEFAULT NULL,
    ci_ig_id       VARCHAR(36)  DEFAULT NULL,

    created_at     DATETIME     NOT NULL,
    updated_at     DATETIME     NOT NULL,

    PRIMARY KEY (id),
    CONSTRAINT uq_event_organiser_event UNIQUE (event_id),

    CONSTRAINT fk_eo_event  FOREIGN KEY (event_id)  REFERENCES event          (id) ON DELETE CASCADE,
    CONSTRAINT fk_eo_ig     FOREIGN KEY (ig_id)     REFERENCES interest_group (id) ON DELETE SET NULL,
    CONSTRAINT fk_eo_org    FOREIGN KEY (org_id)    REFERENCES organization   (id) ON DELETE SET NULL,
    CONSTRAINT fk_eo_ci_org FOREIGN KEY (ci_org_id) REFERENCES organization   (id) ON DELETE SET NULL,
    CONSTRAINT fk_eo_ci_ig  FOREIGN KEY (ci_ig_id)  REFERENCES interest_group (id) ON DELETE SET NULL
);


-- ============================================================================
-- M6. EVENT COLLABORATORS (many per event)
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_collaborator
(
    id                VARCHAR(36)  NOT NULL,
    event_id          VARCHAR(36)  NOT NULL,
    collaborator_type ENUM('ig', 'campus', 'campus_ig', 'company') NOT NULL,

    ig_id             VARCHAR(36)  DEFAULT NULL,
    org_id            VARCHAR(36)  DEFAULT NULL,
    ci_org_id         VARCHAR(36)  DEFAULT NULL,
    ci_ig_id          VARCHAR(36)  DEFAULT NULL,

    role_label        VARCHAR(100) DEFAULT NULL,
    invite_status     ENUM('pending', 'accepted', 'rejected') NOT NULL DEFAULT 'pending',
    rejection_reason  VARCHAR(500) DEFAULT NULL,
    invited_at        DATETIME     NOT NULL,
    responded_at      DATETIME     DEFAULT NULL,

    created_by        VARCHAR(36)  NOT NULL,
    created_at        DATETIME     NOT NULL,

    PRIMARY KEY (id),

    CONSTRAINT uq_ec_ig  UNIQUE (event_id, ig_id),
    CONSTRAINT uq_ec_org UNIQUE (event_id, org_id),
    CONSTRAINT uq_ec_ci  UNIQUE (event_id, ci_org_id, ci_ig_id),

    CONSTRAINT fk_ec_event   FOREIGN KEY (event_id)   REFERENCES event          (id) ON DELETE CASCADE,
    CONSTRAINT fk_ec_ig      FOREIGN KEY (ig_id)      REFERENCES interest_group (id) ON DELETE CASCADE,
    CONSTRAINT fk_ec_org     FOREIGN KEY (org_id)      REFERENCES organization   (id) ON DELETE CASCADE,
    CONSTRAINT fk_ec_ci_org  FOREIGN KEY (ci_org_id)  REFERENCES organization   (id) ON DELETE CASCADE,
    CONSTRAINT fk_ec_ci_ig   FOREIGN KEY (ci_ig_id)   REFERENCES interest_group (id) ON DELETE CASCADE,
    CONSTRAINT fk_ec_created FOREIGN KEY (created_by) REFERENCES user           (id) ON DELETE RESTRICT
);


-- ============================================================================
-- M7. EVENT INTEREST ("I'M GOING")
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_interest
(
    id           VARCHAR(36)  NOT NULL,
    event_id     VARCHAR(36)  NOT NULL,
    user_id      VARCHAR(36)  NOT NULL,
    expressed_at DATETIME     NOT NULL,

    PRIMARY KEY (id),
    CONSTRAINT uq_event_interest UNIQUE (event_id, user_id),

    CONSTRAINT fk_ei_event FOREIGN KEY (event_id) REFERENCES event (id) ON DELETE CASCADE,
    CONSTRAINT fk_ei_user  FOREIGN KEY (user_id)  REFERENCES user  (id) ON DELETE CASCADE
);


-- ============================================================================
-- M8. EVENT EDIT AUDIT LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_edit_log
(
    id             VARCHAR(36)  NOT NULL,
    event_id       VARCHAR(36)  NOT NULL,
    edited_by      VARCHAR(36)  NOT NULL,
    changed_fields JSON         NOT NULL,
    edited_at      DATETIME     NOT NULL,

    PRIMARY KEY (id),

    CONSTRAINT fk_eel_event  FOREIGN KEY (event_id)  REFERENCES event (id) ON DELETE CASCADE,
    CONSTRAINT fk_eel_editor FOREIGN KEY (edited_by) REFERENCES user  (id) ON DELETE RESTRICT
);


-- ============================================================================
-- M8.1. ADD cluster COLUMN TO interest_group (guarded)
-- ============================================================================

SET @col_exists = (
    SELECT COUNT(*)
    FROM   information_schema.COLUMNS
    WHERE  TABLE_SCHEMA = DATABASE()
      AND  TABLE_NAME   = 'interest_group'
      AND  COLUMN_NAME  = 'cluster'
);

SET @sql = IF(
    @col_exists = 0,
    'ALTER TABLE interest_group
         ADD COLUMN cluster ENUM(''coder'',''maker'',''manager'',''creative'')
         DEFAULT NULL
         AFTER name',
    'SELECT ''interest_group.cluster already exists — skipping'' AS migration_note'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Index on cluster (IF NOT EXISTS is supported for CREATE INDEX in MySQL 8)
CREATE INDEX IF NOT EXISTS idx_ig_cluster ON interest_group (cluster);


-- ============================================================================
-- M8.2. EVENT CO-OWNERS
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_co_owner
(
    id       VARCHAR(36)  NOT NULL,
    event_id VARCHAR(36)  NOT NULL,
    user_id  VARCHAR(36)  NOT NULL,
    role     ENUM('co_owner', 'admin') NOT NULL DEFAULT 'co_owner',
    added_by VARCHAR(36)  NOT NULL,
    added_at DATETIME     NOT NULL,

    PRIMARY KEY (id),
    CONSTRAINT uq_eco_event_user UNIQUE (event_id, user_id),

    CONSTRAINT fk_eco_event    FOREIGN KEY (event_id) REFERENCES event (id) ON DELETE CASCADE,
    CONSTRAINT fk_eco_user     FOREIGN KEY (user_id)  REFERENCES user  (id) ON DELETE CASCADE,
    CONSTRAINT fk_eco_added_by FOREIGN KEY (added_by) REFERENCES user  (id) ON DELETE RESTRICT
);


-- ============================================================================
-- M9. MODIFY task_list — RENAME event → event_id + FK (both guarded)
-- ============================================================================

-- Step 1: rename column only if the old name still exists
SET @old_col_exists = (
    SELECT COUNT(*)
    FROM   information_schema.COLUMNS
    WHERE  TABLE_SCHEMA = DATABASE()
      AND  TABLE_NAME   = 'task_list'
      AND  COLUMN_NAME  = 'event'
);

SET @sql = IF(
    @old_col_exists > 0,
    'ALTER TABLE task_list
         CHANGE COLUMN `event` `event_id` VARCHAR(36) DEFAULT NULL',
    'SELECT ''task_list.event already renamed — skipping CHANGE COLUMN'' AS migration_note'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Step 2: add FK only if it does not already exist
SET @fk_exists = (
    SELECT COUNT(*)
    FROM   information_schema.TABLE_CONSTRAINTS
    WHERE  TABLE_SCHEMA     = DATABASE()
      AND  TABLE_NAME       = 'task_list'
      AND  CONSTRAINT_NAME  = 'fk_task_list_event_id'
      AND  CONSTRAINT_TYPE  = 'FOREIGN KEY'
);

SET @sql = IF(
    @fk_exists = 0,
    'ALTER TABLE task_list
         ADD CONSTRAINT fk_task_list_event_id
         FOREIGN KEY (event_id) REFERENCES event (id) ON DELETE SET NULL',
    'SELECT ''fk_task_list_event_id already exists — skipping ADD CONSTRAINT'' AS migration_note'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ============================================================================
-- M10. PERFORMANCE INDEXES
-- ============================================================================

-- event feed
CREATE INDEX IF NOT EXISTS idx_event_status_start ON event (status, start_datetime);
CREATE INDEX IF NOT EXISTS idx_event_deleted_at    ON event (deleted_at);
CREATE INDEX IF NOT EXISTS idx_event_featured      ON event (is_featured, status);

-- event_scope visibility
CREATE INDEX IF NOT EXISTS idx_es_campus    ON event_scope (scope, target_org_id);
CREATE INDEX IF NOT EXISTS idx_es_ig        ON event_scope (scope, target_ig_id);
CREATE INDEX IF NOT EXISTS idx_es_campus_ig ON event_scope (scope, target_ci_org_id, target_ci_ig_id);

-- event_organiser lookups
CREATE INDEX IF NOT EXISTS idx_eo_ig        ON event_organiser (organiser_type, ig_id);
CREATE INDEX IF NOT EXISTS idx_eo_org       ON event_organiser (organiser_type, org_id);
CREATE INDEX IF NOT EXISTS idx_eo_campus_ig ON event_organiser (organiser_type, ci_org_id, ci_ig_id);

-- event_collaborator
CREATE INDEX IF NOT EXISTS idx_ec_ig          ON event_collaborator (ig_id, invite_status);
CREATE INDEX IF NOT EXISTS idx_ec_org         ON event_collaborator (org_id, invite_status);
CREATE INDEX IF NOT EXISTS idx_ec_event_status ON event_collaborator (event_id, invite_status);

-- event_interest
CREATE INDEX IF NOT EXISTS idx_ei_event ON event_interest (event_id);
CREATE INDEX IF NOT EXISTS idx_ei_user  ON event_interest (user_id);

-- task_list → event join
CREATE INDEX IF NOT EXISTS idx_task_event_id ON task_list (event_id);

-- event_tag_link
CREATE INDEX IF NOT EXISTS idx_etl_tag ON event_tag_link (tag_id);

-- event_edit_log audit
CREATE INDEX IF NOT EXISTS idx_eel_event_time ON event_edit_log (event_id, edited_at);

-- event_co_owner
CREATE INDEX IF NOT EXISTS idx_eco_user  ON event_co_owner (user_id);
CREATE INDEX IF NOT EXISTS idx_eco_event ON event_co_owner (event_id);


-- ============================================================================
-- M11. INTEREST COUNT TRIGGERS
-- ============================================================================

DROP TRIGGER IF EXISTS trg_event_interest_insert;

CREATE TRIGGER trg_event_interest_insert
    AFTER INSERT ON event_interest
    FOR EACH ROW
    UPDATE event
    SET    interest_count = interest_count + 1
    WHERE  id = NEW.event_id;


DROP TRIGGER IF EXISTS trg_event_interest_delete;

CREATE TRIGGER trg_event_interest_delete
    AFTER DELETE ON event_interest
    FOR EACH ROW
    UPDATE event
    SET    interest_count = GREATEST(interest_count - 1, 0)
    WHERE  id = OLD.event_id;


-- ============================================================================
-- VERIFICATION
-- ============================================================================

SELECT
    table_name,
    table_rows,
    create_time
FROM   information_schema.tables
WHERE  table_schema = DATABASE()
  AND  table_name IN (
      'event', 'event_tag', 'event_tag_link',
      'event_venue', 'event_scope', 'event_organiser',
      'event_collaborator', 'event_interest',
      'event_edit_log', 'event_co_owner'
  )
ORDER BY table_name;

-- Confirm exactly 10 new tables exist
SELECT
    COUNT(*) AS tables_created,
    IF(COUNT(*) = 10, 'PASS', 'FAIL — expected 10') AS check_result
FROM   information_schema.tables
WHERE  table_schema = DATABASE()
  AND  table_name IN (
      'event', 'event_tag', 'event_tag_link',
      'event_venue', 'event_scope', 'event_organiser',
      'event_collaborator', 'event_interest',
      'event_edit_log', 'event_co_owner'
  );

-- Confirm cluster column landed on interest_group
SELECT
    column_name,
    column_type,
    is_nullable,
    column_default
FROM   information_schema.columns
WHERE  table_schema = DATABASE()
  AND  table_name   = 'interest_group'
  AND  column_name  = 'cluster';

-- Confirm task_list.event_id exists and old `event` column is gone
SELECT
    column_name,
    column_type,
    is_nullable
FROM   information_schema.columns
WHERE  table_schema = DATABASE()
  AND  table_name   = 'task_list'
  AND  column_name  IN ('event', 'event_id')
ORDER BY column_name;

-- Confirm triggers exist
SELECT
    trigger_name,
    event_manipulation,
    event_object_table,
    action_timing
FROM   information_schema.triggers
WHERE  trigger_schema = DATABASE()
  AND  trigger_name IN (
      'trg_event_interest_insert',
      'trg_event_interest_delete'
  );

-- Confirm all FKs are registered
SELECT
    constraint_name,
    table_name,
    referenced_table_name
FROM   information_schema.referential_constraints
WHERE  constraint_schema = DATABASE()
  AND  constraint_name IN (
      'fk_event_created_by', 'fk_event_updated_by', 'fk_event_deleted_by',
      'fk_etl_event', 'fk_etl_tag',
      'fk_event_venue_event',
      'fk_es_event', 'fk_es_org', 'fk_es_ig', 'fk_es_ci_org', 'fk_es_ci_ig',
      'fk_eo_event', 'fk_eo_ig', 'fk_eo_org', 'fk_eo_ci_org', 'fk_eo_ci_ig',
      'fk_ec_event', 'fk_ec_ig', 'fk_ec_org', 'fk_ec_ci_org', 'fk_ec_ci_ig', 'fk_ec_created',
      'fk_ei_event', 'fk_ei_user',
      'fk_eel_event', 'fk_eel_editor',
      'fk_eco_event', 'fk_eco_user', 'fk_eco_added_by',
      'fk_task_list_event_id'
  )
ORDER BY table_name, constraint_name;

SELECT 'ALTER 1.92 — migration complete' AS status;