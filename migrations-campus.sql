-- ============================================================
-- ALTER 1.93 — Campus Dashboard: IG Chapters & Social Links
-- Prerequisite: ALTER 1.92 (Events System) must be applied first
-- ============================================================

-- 1. campus_ig_chapter
CREATE TABLE IF NOT EXISTS campus_ig_chapter
(
    id            VARCHAR(36) PRIMARY KEY NOT NULL,
    org_id        VARCHAR(36)             NOT NULL,
    ig_id         VARCHAR(36)             NOT NULL,
    lead_user_id  VARCHAR(36),
    is_active     BOOLEAN DEFAULT TRUE    NOT NULL,
    created_by    VARCHAR(36)             NOT NULL,
    created_at    DATETIME                NOT NULL,
    updated_by    VARCHAR(36)             NOT NULL,
    updated_at    DATETIME                NOT NULL,

    CONSTRAINT uq_cic_org_ig   UNIQUE (org_id, ig_id),

    CONSTRAINT fk_cic_org      FOREIGN KEY (org_id)       REFERENCES organization   (id) ON DELETE CASCADE,
    CONSTRAINT fk_cic_ig       FOREIGN KEY (ig_id)        REFERENCES interest_group (id) ON DELETE CASCADE,
    CONSTRAINT fk_cic_lead     FOREIGN KEY (lead_user_id) REFERENCES user           (id) ON DELETE SET NULL,
    CONSTRAINT fk_cic_created  FOREIGN KEY (created_by)   REFERENCES user           (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cic_updated  FOREIGN KEY (updated_by)   REFERENCES user           (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_cic_org    ON campus_ig_chapter (org_id);
CREATE INDEX IF NOT EXISTS idx_cic_ig     ON campus_ig_chapter (ig_id);
CREATE INDEX IF NOT EXISTS idx_cic_lead   ON campus_ig_chapter (lead_user_id);


-- 2. campus_social_link
CREATE TABLE IF NOT EXISTS campus_social_link
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    org_id     VARCHAR(36)             NOT NULL,
    platform   VARCHAR(30)             NOT NULL,
    url        VARCHAR(500)            NOT NULL,
    label      VARCHAR(100),
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,

    CONSTRAINT uq_csl_org_platform UNIQUE (org_id, platform),

    CONSTRAINT fk_csl_org      FOREIGN KEY (org_id)     REFERENCES organization (id) ON DELETE CASCADE,
    CONSTRAINT fk_csl_created  FOREIGN KEY (created_by) REFERENCES user         (id) ON DELETE RESTRICT,
    CONSTRAINT fk_csl_updated  FOREIGN KEY (updated_by) REFERENCES user         (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_csl_org ON campus_social_link (org_id);


-- 3. campus_execom_role  (admin-managed campus governance roles)
CREATE TABLE IF NOT EXISTS campus_execom_role
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    title      VARCHAR(100)            NOT NULL UNIQUE,
    priority   INT DEFAULT 0           NOT NULL,
    is_active  BOOLEAN DEFAULT TRUE    NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,

    CONSTRAINT fk_cer_created FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cer_updated FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE RESTRICT
);


-- 4. campus_execom  (campus-level user ↔ execom role assignment)
CREATE TABLE IF NOT EXISTS campus_execom
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    org_id     VARCHAR(36)             NOT NULL,
    user_id    VARCHAR(36)             NOT NULL,
    role_id    VARCHAR(36)             NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,

    CONSTRAINT uq_ce_org_user_role UNIQUE (org_id, user_id, role_id),

    CONSTRAINT fk_ce_org     FOREIGN KEY (org_id)     REFERENCES organization        (id) ON DELETE CASCADE,
    CONSTRAINT fk_ce_user    FOREIGN KEY (user_id)    REFERENCES user                (id) ON DELETE CASCADE,
    CONSTRAINT fk_ce_role    FOREIGN KEY (role_id)    REFERENCES campus_execom_role   (id) ON DELETE CASCADE,
    CONSTRAINT fk_ce_created FOREIGN KEY (created_by) REFERENCES user                (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_ce_org  ON campus_execom (org_id);
CREATE INDEX IF NOT EXISTS idx_ce_user ON campus_execom (user_id);
CREATE INDEX IF NOT EXISTS idx_ce_role ON campus_execom (role_id);
