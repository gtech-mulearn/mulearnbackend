-- ============================================================================
-- ALTER 1.92 — Events System Migration
-- Target DB: MySQL 8.0+
-- Run sections M1 → M11 in order. Each section is idempotent.
-- ============================================================================


-- ============================================================================
-- M1. CORE EVENT TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS event
(
    id                    VARCHAR(36)  PRIMARY KEY NOT NULL,

    -- Content
    title                 VARCHAR(200)             NOT NULL,
    slug                  VARCHAR(220)             NOT NULL,
    description           TEXT                     NOT NULL,
    cover_image           VARCHAR(500),
    banner_image          VARCHAR(500),

    -- Classification
    event_type            ENUM(
                              'workshop', 'webinar', 'hackathon',
                              'meetup', 'competition', 'social_gathering', 'other'
                          )                        NOT NULL DEFAULT 'other',

    -- Lifecycle
    status                ENUM(
                              'draft', 'pending_campus_approval',
                              'pending_approval', 'pending_mentor_approval',
                              'published', 'ongoing', 'completed', 'cancelled'
                          )                        NOT NULL DEFAULT 'draft',

    -- Dates
    start_datetime        DATETIME                 NOT NULL,
    end_datetime          DATETIME                 NOT NULL,

    -- External registration
    registration_url      VARCHAR(500),
    registration_deadline DATETIME,

    -- Karma eligibility gate (threshold check, NOT deducted)
    min_karma             BIGINT       UNSIGNED    DEFAULT NULL,

    -- Collaboration & curation flags
    is_collaboration      BOOLEAN      DEFAULT FALSE NOT NULL,
    is_featured           BOOLEAN      DEFAULT FALSE NOT NULL,

    -- Denormalised counter kept in sync by triggers (see M11)
    interest_count        INT UNSIGNED DEFAULT 0    NOT NULL,

    -- Audit
    created_by            VARCHAR(36)              NOT NULL,
    created_at            DATETIME                 NOT NULL,
    updated_by            VARCHAR(36)              NOT NULL,
    updated_at            DATETIME                 NOT NULL,
    deleted_at            DATETIME,
    deleted_by            VARCHAR(36),

    CONSTRAINT uq_event_slug           UNIQUE (slug),
    CONSTRAINT chk_event_dates         CHECK  (end_datetime > start_datetime),
    CONSTRAINT chk_event_min_karma     CHECK  (min_karma IS NULL OR min_karma >= 0),

    CONSTRAINT fk_event_created_by     FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE RESTRICT,
    CONSTRAINT fk_event_updated_by     FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE RESTRICT,
    CONSTRAINT fk_event_deleted_by     FOREIGN KEY (deleted_by) REFERENCES user (id) ON DELETE SET NULL
);


-- ============================================================================
-- M2. EVENT TAGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_tag
(
    id         VARCHAR(36)  PRIMARY KEY NOT NULL,
    name       VARCHAR(50)  UNIQUE      NOT NULL,
    created_at DATETIME                 NOT NULL
);

CREATE TABLE IF NOT EXISTS event_tag_link
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id   VARCHAR(36)             NOT NULL,
    tag_id     VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,

    CONSTRAINT uq_event_tag_link        UNIQUE      (event_id, tag_id),
    CONSTRAINT fk_etl_event             FOREIGN KEY (event_id) REFERENCES event     (id) ON DELETE CASCADE,
    CONSTRAINT fk_etl_tag               FOREIGN KEY (tag_id)   REFERENCES event_tag (id) ON DELETE CASCADE
);


-- ============================================================================
-- M3. EVENT VENUE (1-to-1 with event)
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_venue
(
    id           VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id     VARCHAR(36) UNIQUE      NOT NULL,
    venue_type   ENUM('physical','online','hybrid') NOT NULL,

    -- Physical / hybrid
    address      VARCHAR(300),
    city         VARCHAR(100),
    maps_url     VARCHAR(500),

    -- Online / hybrid
    online_link  VARCHAR(500),
    platform     VARCHAR(100),

    created_at   DATETIME NOT NULL,
    updated_at   DATETIME NOT NULL,

    CONSTRAINT fk_event_venue_event FOREIGN KEY (event_id) REFERENCES event (id) ON DELETE CASCADE
);


-- ============================================================================
-- M4. EVENT SCOPE & TARGETING (1-to-1 with event)
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_scope
(
    id               VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id         VARCHAR(36) UNIQUE      NOT NULL,
    scope            ENUM('global','campus','ig','campus_ig') NOT NULL DEFAULT 'global',

    target_org_id    VARCHAR(36),
    target_ig_id     VARCHAR(36),
    target_ci_org_id VARCHAR(36),
    target_ci_ig_id  VARCHAR(36),

    created_at       DATETIME        NOT NULL,
    updated_at       DATETIME        NOT NULL,

    CONSTRAINT fk_es_event      FOREIGN KEY (event_id)         REFERENCES event          (id) ON DELETE CASCADE,
    CONSTRAINT fk_es_org        FOREIGN KEY (target_org_id)    REFERENCES organization   (id) ON DELETE SET NULL,
    CONSTRAINT fk_es_ig         FOREIGN KEY (target_ig_id)     REFERENCES interest_group (id) ON DELETE SET NULL,
    CONSTRAINT fk_es_ci_org     FOREIGN KEY (target_ci_org_id) REFERENCES organization   (id) ON DELETE SET NULL,
    CONSTRAINT fk_es_ci_ig      FOREIGN KEY (target_ci_ig_id)  REFERENCES interest_group (id) ON DELETE SET NULL
);


-- ============================================================================
-- M5. EVENT ORGANISER (1-to-1 with event)
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_organiser
(
    id             VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id       VARCHAR(36) UNIQUE      NOT NULL,
    organiser_type ENUM('global_ig','campus_ig','campus','company','admin') NOT NULL,

    ig_id          VARCHAR(36),
    org_id         VARCHAR(36),
    ci_org_id      VARCHAR(36),
    ci_ig_id       VARCHAR(36),

    created_at     DATETIME        NOT NULL,
    updated_at     DATETIME        NOT NULL,

    CONSTRAINT fk_eo_event    FOREIGN KEY (event_id)  REFERENCES event          (id) ON DELETE CASCADE,
    CONSTRAINT fk_eo_ig       FOREIGN KEY (ig_id)     REFERENCES interest_group (id) ON DELETE SET NULL,
    CONSTRAINT fk_eo_org      FOREIGN KEY (org_id)    REFERENCES organization   (id) ON DELETE SET NULL,
    CONSTRAINT fk_eo_ci_org   FOREIGN KEY (ci_org_id) REFERENCES organization   (id) ON DELETE SET NULL,
    CONSTRAINT fk_eo_ci_ig    FOREIGN KEY (ci_ig_id)  REFERENCES interest_group (id) ON DELETE SET NULL
);


-- ============================================================================
-- M6. EVENT COLLABORATORS (many per event)
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_collaborator
(
    id                VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id          VARCHAR(36)             NOT NULL,
    collaborator_type ENUM('ig','campus','campus_ig','company') NOT NULL,

    ig_id             VARCHAR(36),
    org_id            VARCHAR(36),
    ci_org_id         VARCHAR(36),
    ci_ig_id          VARCHAR(36),

    role_label        VARCHAR(100),
    invite_status     ENUM('pending','accepted','rejected') NOT NULL DEFAULT 'pending',
    rejection_reason  VARCHAR(500),
    invited_at        DATETIME        NOT NULL,
    responded_at      DATETIME,

    created_by        VARCHAR(36)     NOT NULL,
    created_at        DATETIME        NOT NULL,

    CONSTRAINT uq_ec_ig       UNIQUE (event_id, ig_id),
    CONSTRAINT uq_ec_org      UNIQUE (event_id, org_id),
    CONSTRAINT uq_ec_ci       UNIQUE (event_id, ci_org_id, ci_ig_id),

    CONSTRAINT fk_ec_event    FOREIGN KEY (event_id)   REFERENCES event          (id) ON DELETE CASCADE,
    CONSTRAINT fk_ec_ig       FOREIGN KEY (ig_id)      REFERENCES interest_group (id) ON DELETE CASCADE,
    CONSTRAINT fk_ec_org      FOREIGN KEY (org_id)     REFERENCES organization   (id) ON DELETE CASCADE,
    CONSTRAINT fk_ec_ci_org   FOREIGN KEY (ci_org_id)  REFERENCES organization   (id) ON DELETE CASCADE,
    CONSTRAINT fk_ec_ci_ig    FOREIGN KEY (ci_ig_id)   REFERENCES interest_group (id) ON DELETE CASCADE,
    CONSTRAINT fk_ec_created  FOREIGN KEY (created_by) REFERENCES user           (id) ON DELETE RESTRICT
);


-- ============================================================================
-- M7. EVENT INTEREST ("I'M GOING")
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_interest
(
    id           VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id     VARCHAR(36)             NOT NULL,
    user_id      VARCHAR(36)             NOT NULL,
    expressed_at DATETIME                NOT NULL,

    CONSTRAINT uq_event_interest         UNIQUE      (event_id, user_id),
    CONSTRAINT fk_ei_event               FOREIGN KEY (event_id) REFERENCES event (id) ON DELETE CASCADE,
    CONSTRAINT fk_ei_user                FOREIGN KEY (user_id)  REFERENCES user  (id) ON DELETE CASCADE
);


-- ============================================================================
-- M8. EVENT EDIT AUDIT LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_edit_log
(
    id             VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id       VARCHAR(36)             NOT NULL,
    edited_by      VARCHAR(36)             NOT NULL,
    changed_fields JSON                    NOT NULL,
    edited_at      DATETIME                NOT NULL,

    CONSTRAINT fk_eel_event  FOREIGN KEY (event_id)  REFERENCES event (id) ON DELETE CASCADE,
    CONSTRAINT fk_eel_editor FOREIGN KEY (edited_by) REFERENCES user  (id) ON DELETE RESTRICT
);


-- ============================================================================
-- M8.1. ADD CLUSTER COLUMN TO interest_group
-- ============================================================================

ALTER TABLE interest_group
    ADD COLUMN IF NOT EXISTS cluster ENUM('coder', 'maker', 'manager', 'creative')
    DEFAULT NULL
    AFTER name;

CREATE INDEX IF NOT EXISTS idx_ig_cluster
    ON interest_group (cluster);


-- ============================================================================
-- M8.2. EVENT CO-OWNERS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_co_owner
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id   VARCHAR(36)             NOT NULL,
    user_id    VARCHAR(36)             NOT NULL,
    role       ENUM('co_owner', 'admin') NOT NULL DEFAULT 'co_owner',
    added_by   VARCHAR(36)             NOT NULL,
    added_at   DATETIME                NOT NULL,

    CONSTRAINT uq_eco_event_user  UNIQUE      (event_id, user_id),

    CONSTRAINT fk_eco_event       FOREIGN KEY (event_id) REFERENCES event (id) ON DELETE CASCADE,
    CONSTRAINT fk_eco_user        FOREIGN KEY (user_id)  REFERENCES user  (id) ON DELETE CASCADE,
    CONSTRAINT fk_eco_added_by    FOREIGN KEY (added_by) REFERENCES user  (id) ON DELETE RESTRICT
);


-- ============================================================================
-- M9. MODIFY task_list — LINK TASKS TO EVENTS
-- ============================================================================

ALTER TABLE task_list
    CHANGE COLUMN `event` `event_id` VARCHAR(36) DEFAULT NULL;

ALTER TABLE task_list
    ADD CONSTRAINT fk_task_list_event_id
    FOREIGN KEY (event_id) REFERENCES event (id) ON DELETE SET NULL;


-- ============================================================================
-- M10. PERFORMANCE INDEXES
-- ============================================================================

-- event: feed filter — status + chronological order
CREATE INDEX IF NOT EXISTS idx_event_status_start
    ON event (status, start_datetime);

-- event: soft-delete filter
CREATE INDEX IF NOT EXISTS idx_event_deleted_at
    ON event (deleted_at);

-- event: homepage featured carousel
CREATE INDEX IF NOT EXISTS idx_event_featured
    ON event (is_featured, status);

-- event_scope: campus visibility
CREATE INDEX IF NOT EXISTS idx_es_campus
    ON event_scope (scope, target_org_id);

-- event_scope: IG visibility
CREATE INDEX IF NOT EXISTS idx_es_ig
    ON event_scope (scope, target_ig_id);

-- event_scope: campus-IG chapter visibility
CREATE INDEX IF NOT EXISTS idx_es_campus_ig
    ON event_scope (scope, target_ci_org_id, target_ci_ig_id);

-- event_organiser: events by IG
CREATE INDEX IF NOT EXISTS idx_eo_ig
    ON event_organiser (organiser_type, ig_id);

-- event_organiser: events by campus/company
CREATE INDEX IF NOT EXISTS idx_eo_org
    ON event_organiser (organiser_type, org_id);

-- event_organiser: events by campus-IG chapter
CREATE INDEX IF NOT EXISTS idx_eo_campus_ig
    ON event_organiser (organiser_type, ci_org_id, ci_ig_id);

-- event_collaborator: IG collaborations
CREATE INDEX IF NOT EXISTS idx_ec_ig
    ON event_collaborator (ig_id, invite_status);

-- event_collaborator: org collaborations
CREATE INDEX IF NOT EXISTS idx_ec_org
    ON event_collaborator (org_id, invite_status);

-- event_collaborator: pending invites per event
CREATE INDEX IF NOT EXISTS idx_ec_event_status
    ON event_collaborator (event_id, invite_status);

-- event_interest: count per event
CREATE INDEX IF NOT EXISTS idx_ei_event
    ON event_interest (event_id);

-- event_interest: user calendar
CREATE INDEX IF NOT EXISTS idx_ei_user
    ON event_interest (user_id);

-- task_list: join tasks to event
CREATE INDEX IF NOT EXISTS idx_task_event_id
    ON task_list (event_id);

-- event_tag_link: tag-based filtering
CREATE INDEX IF NOT EXISTS idx_etl_tag
    ON event_tag_link (tag_id);

-- event_edit_log: audit history
CREATE INDEX IF NOT EXISTS idx_eel_event_time
    ON event_edit_log (event_id, edited_at);

-- event_co_owner: user lookups
CREATE INDEX IF NOT EXISTS idx_eco_user
    ON event_co_owner (user_id);

-- event_co_owner: per-event lookups
CREATE INDEX IF NOT EXISTS idx_eco_event
    ON event_co_owner (event_id);


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
-- MIGRATION COMPLETE
-- ============================================================================
