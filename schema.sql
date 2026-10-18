-- ============================================================
-- MuLearn DEV database: full schema (reconstructed)
-- Part A: latest.sql (production schema, unchanged)
-- Part B: dev delta (what pranav-dev models need on top of prod)
-- Part C: company problem statements (db-scripts/alter/alter-1.91.sql)
-- Verified (Parts A+B): loads with no errors on MySQL 8.0 and every Django model SELECTs OK.
-- Part C is the same SQL as alter-1.91, already applied on mu_dev; the full file
-- has not yet been re-loaded end to end with Part C included.
-- ============================================================


-- ---------- PART A: latest.sql ----------
CREATE TABLE user
(
    id             VARCHAR(36) PRIMARY KEY NOT NULL,
    discord_id     VARCHAR(36) UNIQUE KEY,
    muid           VARCHAR(100) UNIQUE KEY NOT NULL,
    full_name      VARCHAR(150)            NOT NULL,
    email          VARCHAR(200) UNIQUE KEY NOT NULL,
    password       VARCHAR(200),
    mobile         VARCHAR(15),
    gender         VARCHAR(10),
    dob            DATE,
    admin          BOOLEAN DEFAULT FALSE   NOT NULL,
    exist_in_guild BOOLEAN DEFAULT FALSE   NOT NULL,
    interested_in_work BOOLEAN DEFAULT      FALSE,
    interested_in_gig_work BOOLEAN DEFAULT  FALSE,
    created_at     DATETIME                NOT NULL,
    deleted_at     DATETIME,
    deleted_by     VARCHAR(36),
    suspended_at   DATETIME,
    suspended_by   VARCHAR(36),
    CONSTRAINT fk_user_ref_deleted_by FOREIGN KEY (deleted_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_ref_suspended_by FOREIGN KEY (suspended_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE wallet
(
    id                    VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id               VARCHAR(36) UNIQUE KEY  NOT NULL,
    karma                 BIGINT DEFAULT 0        NOT NULL,
    karma_last_updated_at DATETIME                NOT NULL,
    coin                  FLOAT  DEFAULT 0        NOT NULL,
    updated_by            VARCHAR(36)             NOT NULL,
    updated_at            DATETIME                NOT NULL,
    created_by            VARCHAR(36)             NOT NULL,
    created_at            DATETIME                NOT NULL,
    CONSTRAINT `fk_total_karma_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_total_karma_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_total_karma_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE role
(
    id             VARCHAR(36) PRIMARY KEY NOT NULL,
    title          VARCHAR(75) UNIQUE KEY  NOT NULL,
    description    VARCHAR(300),
    is_execom_role TINYINT(1)              NOT NULL DEFAULT 0,
    updated_by     VARCHAR(36)             NOT NULL,
    updated_at     DATETIME                NOT NULL,
    created_by     VARCHAR(36)             NOT NULL,
    created_at     DATETIME                NOT NULL,
    CONSTRAINT `fk_role_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_role_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE user_role_link
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id    VARCHAR(36)             NOT NULL,
    role_id    VARCHAR(36)             NOT NULL,
    verified   BOOLEAN DEFAULT FALSE   NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT `fk_user_role_link_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_role_link_ref_role_id` FOREIGN KEY (`role_id`) REFERENCES `role` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_role_link_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE org_affiliation
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    title      VARCHAR(75)             NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT `fk_org_affiliation_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_org_affiliation_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE country
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    name       VARCHAR(75)             NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT `fk_country_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_country_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE state
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    name       VARCHAR(75)             NOT NULL,
    country_id VARCHAR(36)             NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT `fk_state_ref_country_id` FOREIGN KEY (`country_id`) REFERENCES `country` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_state_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_state_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE zone
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    name       VARCHAR(75)             NOT NULL,
    state_id   VARCHAR(36)             NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT `fk_zone_ref_state_id` FOREIGN KEY (`state_id`) REFERENCES `state` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_zone_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_zone_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE district
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    name       VARCHAR(75)             NOT NULL,
    zone_id    VARCHAR(36)             NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT `fk_district_ref_zone_id` FOREIGN KEY (`zone_id`) REFERENCES `zone` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_district_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_district_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE organization
(
    id             VARCHAR(36) PRIMARY KEY NOT NULL,
    title          VARCHAR(100)            NOT NULL,
    code           VARCHAR(12) UNIQUE KEY  NOT NULL,
    org_type       VARCHAR(25)             NOT NULL,
    affiliation_id VARCHAR(36),
    district_id    VARCHAR(36),
    cached_total_karma  INT DEFAULT 0        NOT NULL,
    cached_member_count INT DEFAULT 0        NOT NULL,
    updated_by     VARCHAR(36)             NOT NULL,
    updated_at     DATETIME                NOT NULL,
    created_by     VARCHAR(36)             NOT NULL,
    created_at     DATETIME                NOT NULL,
    KEY `idx_organization_org_type_karma` (`org_type`,`cached_total_karma`),
    KEY `idx_organization_org_type_members` (`org_type`,`cached_member_count`),
    CONSTRAINT `fk_organization_ref_affiliation_id` FOREIGN KEY (`affiliation_id`) REFERENCES `org_affiliation` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_organization_ref_district_id` FOREIGN KEY (`district_id`) REFERENCES `district` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_organization_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_organization_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE department
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    title      VARCHAR(100)            NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT `fk_department_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_department_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE user_organization_link
(
    id              VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id         VARCHAR(36)             NOT NULL,
    org_id          VARCHAR(36)             NOT NULL,
    department_id   VARCHAR(36),
    graduation_year VARCHAR(10),
    verified        BOOLEAN DEFAULT FALSE   NOT NULL,
    is_alumni       BOOLEAN DEFAULT FALSE   NOT NULL,
    created_by      VARCHAR(36)             NOT NULL,
    created_at      DATETIME                NOT NULL,
    KEY `idx_user_organization_link_org_verified` (`org_id`,`verified`),
    CONSTRAINT `fk_user_organization_link_ref_department_id` FOREIGN KEY (`department_id`) REFERENCES `department` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_organization_link_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_organization_link_ref_org_id` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_organization_link_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE interest_group
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    name       VARCHAR(75) UNIQUE KEY  NOT NULL,
    code       VARCHAR(5) UNIQUE KEY   NOT NULL,
    icon       VARCHAR(10)             NULL DEFAULT NULL,
    category   VARCHAR(20)             NOT NULL DEFAULT "others",
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT `fk_interest_group_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_interest_group_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE user_ig_link
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id    VARCHAR(36)             NOT NULL,
    ig_id      VARCHAR(36)             NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT `fk_user_ig_link_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_ig_link_ref_ig_id` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_ig_link_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE channel
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    name       VARCHAR(75) UNIQUE KEY  NOT NULL,
    discord_id VARCHAR(36)             NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT `fk_channel_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_channel_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE task_type
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    title      VARCHAR(75)             NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT `fk_task_type_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_task_type_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE level
(
    id          VARCHAR(36) PRIMARY KEY NOT NULL,
    level_order INTEGER                 NOT NULL,
    name        VARCHAR(36) UNIQUE KEY  NOT NULL,
    karma       INTEGER                 NOT NULL,
    created_by  VARCHAR(36)             NOT NULL,
    created_at  DATETIME                NOT NULL,
    updated_by  VARCHAR(36)             NOT NULL,
    updated_at  DATETIME                NOT NULL,
    CONSTRAINT fk_level_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_level_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE user_lvl_link
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id    VARCHAR(75) UNIQUE KEY  NOT NULL,
    level_id   VARCHAR(75)             NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT fk_user_lvl_link_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_lvl_link_ref_level_id FOREIGN KEY (level_id) REFERENCES level (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_lvl_link_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_lvl_link_ref_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE user_lvl_log
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id    VARCHAR(75)             NOT NULL,
    level_id   VARCHAR(75)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT fk_user_lvl_log_ref_level_id FOREIGN KEY (level_id) REFERENCES level (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_lvl_log_ref_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE task_list
(
    id             VARCHAR(36) PRIMARY KEY NOT NULL,
    hashtag        VARCHAR(75)             NOT NULL,
    discord_link   VARCHAR(200),
    title          VARCHAR(75)             NOT NULL,
    description    VARCHAR(200),
    karma          INTEGER,
    channel_id     VARCHAR(36),
    type_id        VARCHAR(36)             NOT NULL,
    org_id         VARCHAR(36),
    level_id       VARCHAR(36),
    ig_id          VARCHAR(36),
    active         BOOLEAN DEFAULT TRUE    NOT NULL,
    variable_karma BOOLEAN DEFAULT FALSE   NOT NULL,
    usage_count    INTEGER DEFAULT 1,
    event          VARCHAR(50),
    bonus_time     DATETIME,
    bonus_karma    INT     DEFAULT 0,
    updated_by     VARCHAR(36)             NOT NULL,
    updated_at     DATETIME                NOT NULL,
    created_by     VARCHAR(36)             NOT NULL,
    created_at     DATETIME                NOT NULL,
    is_deleted     TINYINT(1) DEFAULT 0    NOT NULL,
    deleted_at     DATETIME,
    deleted_by     VARCHAR(36),
    CONSTRAINT `fk_task_list_ref_level_id` FOREIGN KEY (level_id) REFERENCES level (id) ON DELETE CASCADE,
    CONSTRAINT `fk_task_list_ref_ig_id` FOREIGN KEY (ig_id) REFERENCES interest_group (id) ON DELETE CASCADE,
    CONSTRAINT `fk_task_list_ref_channel_id` FOREIGN KEY (`channel_id`) REFERENCES `channel` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_task_list_ref_type_id` FOREIGN KEY (`type_id`) REFERENCES `task_type` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_task_list_ref_org_id` FOREIGN KEY (org_id) REFERENCES organization (id) ON DELETE CASCADE,
    CONSTRAINT `fk_task_list_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_task_list_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_task_list_ref_deleted_by` FOREIGN KEY (deleted_by) REFERENCES user (id) ON DELETE SET NULL,
    INDEX `idx_task_list_is_deleted` (is_deleted)
);

CREATE TABLE karma_activity_log
(
    id                    VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id               VARCHAR(36)             NOT NULL,
    karma                 INTEGER DEFAULT 0       NOT NULL,
    task_id               VARCHAR(36)             NOT NULL,
    task_message_id       VARCHAR(36)             NULL,
    lobby_message_id      VARCHAR(36),
    dm_message_id         VARCHAR(36),
    peer_approved         BOOLEAN,
    peer_approved_by      VARCHAR(36),
    appraiser_approved    BOOLEAN,
    appraiser_approved_by VARCHAR(36),
    updated_by            VARCHAR(36)             NOT NULL,
    updated_at            DATETIME                NOT NULL,
    created_by            VARCHAR(36)             NOT NULL,
    created_at            DATETIME                NOT NULL,
    CONSTRAINT `fk_karma_activity_log_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_karma_activity_log_ref_task_id` FOREIGN KEY (`task_id`) REFERENCES `task_list` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_karma_activity_log_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_karma_activity_log_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE socials
(
    id            VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id       VARCHAR(36)             NOT NULL,
    github        VARCHAR(60),
    facebook      VARCHAR(60),
    instagram     VARCHAR(60),
    linkedin      VARCHAR(60),
    dribble       VARCHAR(60),
    behance       VARCHAR(60),
    stackoverflow VARCHAR(60),
    medium        VARCHAR(60),
    hackerrank    VARCHAR(60),
    updated_by    VARCHAR(36)             NOT NULL,
    updated_at    DATETIME                NOT NULL,
    created_by    VARCHAR(36)             NOT NULL,
    created_at    DATETIME                NOT NULL,
    CONSTRAINT `fk_socials_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_socials_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (id) ON DELETE CASCADE,
    CONSTRAINT `fk_socials_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (id) ON DELETE CASCADE
);

CREATE TABLE forgot_password
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id    VARCHAR(36)             NOT NULL,
    expiry     DATETIME                NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT `fk_forget_password_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE

);

CREATE TABLE system_setting
(
    `key`      VARCHAR(100) PRIMARY KEY NOT NULL,
    value      VARCHAR(100)             NOT NULL,
    updated_at DATETIME                 NOT NULL,
    created_at DATETIME                 NOT NULL
);

CREATE TABLE otp_verification
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id    VARCHAR(36)             NOT NULL,
    otp        INTEGER                 NOT NULL,
    expiry     DATETIME                NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT `fk_otp_verification_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE url_shortener
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    title      VARCHAR(100)            NOT NULL,
    short_url  VARCHAR(100) UNIQUE KEY NOT NULL,
    long_url   VARCHAR(500)            NOT NULL,
    count      INT DEFAULT 0           NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT `fk_url_shorten_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_url_shorten_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE url_shortener_tracker
(
    id               VARCHAR(36) PRIMARY KEY NOT NULL,
    url_shortener_id VARCHAR(36),
    ip_address       VARCHAR(45),
    browser          VARCHAR(255),
    operating_system VARCHAR(255),
    version          VARCHAR(255),
    device_type      VARCHAR(255),
    city             VARCHAR(36),
    region           VARCHAR(36),
    country          VARCHAR(36),
    location         VARCHAR(36),
    referrer         VARCHAR(36),
    created_at       DATETIME                NOT NULL,
    CONSTRAINT `fk_url_shortener_tracker_ref_url_shortener_id` FOREIGN KEY (`url_shortener_id`) REFERENCES `url_shortener` (`id`) ON DELETE CASCADE
);

CREATE TABLE org_discord_link
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    discord_id VARCHAR(36) UNIQUE KEY  NOT NULL,
    org_id     VARCHAR(36) UNIQUE KEY  NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT fk_college_discord_link_ref_org_id FOREIGN KEY (org_id) REFERENCES organization (id) ON DELETE CASCADE,
    CONSTRAINT fk_org_discord_link_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_org_discord_link_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE hackathon
(
    id                VARCHAR(36) PRIMARY KEY NOT NULL,
    title             VARCHAR(100)            NOT NULL,
    tagline           VARCHAR(150),
    description       VARCHAR(5000),
    participant_count INT,
    type              VARCHAR(8) DEFAULT 'offline',
    website           VARCHAR(200),
    org_id            VARCHAR(36),
    district_id       VARCHAR(36),
    place             VARCHAR(255),
    event_logo        VARCHAR(200),
    banner            VARCHAR(200),
    is_open_to_all    BOOLEAN,
    application_start DATETIME,
    application_ends  DATETIME,
    event_start       DATETIME,
    event_end         DATETIME,
    status            VARCHAR(20),
    updated_by        VARCHAR(36)             NOT NULL,
    updated_at        DATETIME                NOT NULL,
    created_by        VARCHAR(36)             NOT NULL,
    created_at        DATETIME                NOT NULL,
    CONSTRAINT fk_hackathon_link_ref_org_id FOREIGN KEY (org_id) REFERENCES organization (id) ON DELETE CASCADE,
    CONSTRAINT fk_hackathon_link_ref_district_id FOREIGN KEY (district_id) REFERENCES district (id) ON DELETE CASCADE,
    CONSTRAINT fk_hackathon_link_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_hackathon_link_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE hackathon_form
(
    id           VARCHAR(36) PRIMARY KEY NOT NULL,
    hackathon_id VARCHAR(36)             NOT NULL,
    field_name   VARCHAR(255)            NOT NULL,
    field_type   VARCHAR(50)             NOT NULL,
    is_required  BOOLEAN DEFAULT false   NOT NULL,
    updated_by   VARCHAR(36)             NOT NULL,
    updated_at   DATETIME                NOT NULL,
    created_by   VARCHAR(36)             NOT NULL,
    created_at   DATETIME                NOT NULL,
    CONSTRAINT fk_hackathon_form_ref_hackathon_id FOREIGN KEY (hackathon_id) REFERENCES hackathon (id) ON DELETE CASCADE,
    CONSTRAINT fk_hackathon_form_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_hackathon_form_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE hackathon_organiser_link
(
    id           VARCHAR(36) PRIMARY KEY NOT NULL,
    organiser_id VARCHAR(36)             NOT NULL,
    hackathon_id VARCHAR(36)             NOT NULL,
    updated_by   VARCHAR(36)             NOT NULL,
    updated_at   DATETIME                NOT NULL,
    created_by   VARCHAR(36)             NOT NULL,
    created_at   DATETIME                NOT NULL,
    CONSTRAINT fk_hackathon_organiser_link_ref_organiser_id FOREIGN KEY (organiser_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_hackathon_organiser_link_ref_hackathon_id FOREIGN KEY (hackathon_id) REFERENCES hackathon (id) ON DELETE CASCADE,
    CONSTRAINT fk_hackathon_organiser_link_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_hackathon_organiser_link_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE hackathon_submission
(
    id           VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id      VARCHAR(36)             NOT NULL,
    hackathon_id VARCHAR(36)             NOT NULL,
    `data`       VARCHAR(2000)           NOT NULL,
    updated_by   VARCHAR(36)             NOT NULL,
    updated_at   DATETIME                NOT NULL,
    created_by   VARCHAR(36)             NOT NULL,
    created_at   DATETIME                NOT NULL,
    CONSTRAINT `fk_hackathon_submission_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_hackathon_submission_ref_hackathon_id` FOREIGN KEY (hackathon_id) REFERENCES hackathon (id) ON DELETE CASCADE,
    CONSTRAINT `fk_hackathon_submission_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_hackathon_submission_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE integration
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    name       VARCHAR(255)            NOT NULL,
    token      VARCHAR(400)            NOT NULL,
    auth_token VARCHAR(255),
    base_url   VARCHAR(255),
    created_at DATETIME                NOT NULL,
    updated_at DATETIME                NOT NULL
);

CREATE TABLE integration_authorization
(
    id                VARCHAR(36) PRIMARY KEY NOT NULL,
    integration_id    VARCHAR(36)             NOT NULL,
    user_id           VARCHAR(36)             NOT NULL,
    integration_value VARCHAR(255) UNIQUE KEY NOT NULL,
    verified          BOOLEAN DEFAULT FALSE   NOT NULL,
    updated_at        DATETIME                NOT NULL,
    created_at        DATETIME                NOT NULL,
    additional_field  VARCHAR(255),
    CONSTRAINT fk_integration_authorization_integration_id FOREIGN KEY (integration_id) REFERENCES integration (id) ON DELETE CASCADE,
    CONSTRAINT fk_integration_authorization_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT unique_integration_per_user_integration_id UNIQUE (integration_id, user_id, integration_value)
);

CREATE TABLE user_settings
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id    VARCHAR(36)             NOT NULL,
    is_public  BOOLEAN DEFAULT FALSE   NOT NULL,
    is_userterms_approved BOOLEAN DEFAULT FALSE NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT fk_user_settings_ref_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_settings_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_settings_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE college
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    level      INT                     NOT NULL,
    org_id     VARCHAR(36)             NOT NULL,
    verified   BOOLEAN DEFAULT FALSE   NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,    
    CONSTRAINT fk_college_ref_org_id FOREIGN KEY (org_id) REFERENCES organization (id) ON DELETE CASCADE,
    CONSTRAINT fk_college_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_college_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE learning_circle
(
    id              VARCHAR(36) PRIMARY KEY NOT NULL,
    title           VARCHAR(100)            NOT NULL,
    description     VARCHAR(1000)           NOT NULL,
    circle_code     VARCHAR(15),
    ig_id           VARCHAR(36)             NOT NULL,
    org_id          VARCHAR(36),
    is_recurring    BOOLEAN DEFAULT TRUE    NOT NULL,
    recurrence_type VARCHAR(10),
    recurrence      INT,
    updated_at  DATETIME                NOT NULL,
    created_by  VARCHAR(36)             NOT NULL,
    created_at  DATETIME                NOT NULL,
    cached_total_karma INT NOT NULL DEFAULT 0,
    cached_rank        INT NOT NULL DEFAULT 0,
    CONSTRAINT fk_learning_circle_ref_college_id FOREIGN KEY (org_id) REFERENCES organization (id) ON DELETE CASCADE,
    CONSTRAINT fk_learning_circle_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_learning_circle_ref_interest_group_id FOREIGN KEY (ig_id) REFERENCES interest_group (id) ON DELETE CASCADE
);

CREATE TABLE circle_meeting_log
(
    id                  VARCHAR(36) PRIMARY KEY NOT NULL,
    circle_id           VARCHAR(36)             NOT NULL,
    meet_code           VARCHAR(6)              NOT NULL,
    title               VARCHAR(100)            NOT NULL,
    description         VARCHAR(1000)           NOT NULL,
    mode                VARCHAR(10)             NOT NULL,
    is_report_needed    BOOLEAN DEFAULT TRUE NOT NULL,
    report_description  VARCHAR(1000),
    coord_x             FLOAT NOT NULL          NOT NULL,
    coord_y             FLOAT NOT NULL          NOT NULL,
    meet_place          VARCHAR(255)            NOT NULL,
    meet_link           VARCHAR(100),
    meet_time           DATETIME                NOT NULL,
    duration            INT                     NOT NULL,
    is_report_submitted BOOLEAN DEFAULT FALSE   NOT NULL,
    is_approved         BOOLEAN DEFAULT FALSE   NOT NULL,
    report_text         VARCHAR(1000),
    created_by          VARCHAR(36)             NOT NULL,
    created_at          DATETIME                NOT NULL,
    updated_at          DATETIME                NOT NULL,
    CONSTRAINT fk_circle_meeting_log_ref_circle_id FOREIGN KEY (circle_id) REFERENCES learning_circle (id) ON DELETE CASCADE,
    CONSTRAINT fk_circle_meeting_log_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE circle_meet_attendees (
    id          VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id     VARCHAR(36)             NOT NULL,
    meet_id     VARCHAR(36)               NOT NULL,
    is_joined   BOOLEAN DEFAULT FALSE   NOT NULL,
    joined_at   DATETIME,
    is_report_submitted BOOLEAN DEFAULT FALSE   NOT NULL,
    is_lc_approved  BOOLEAN DEFAULT FALSE   NOT NULL,
    report_text VARCHAR(1000),
    report_link VARCHAR(200),
    created_at  DATETIME                NOT NULL,
    updated_at  DATETIME                NOT NULL,
    CONSTRAINT fk_circle_meet_attendees_ref_meet_id FOREIGN KEY (meet_id) REFERENCES circle_meeting_log (id) ON DELETE CASCADE,
    CONSTRAINT fk_circle_meet_attendees_ref_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE user_circle_link
(
    id          VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id     VARCHAR(36)             NOT NULL,
    circle_id   VARCHAR(36)             NOT NULL,
    `lead`      BOOLEAN,
    is_invited  TINYINT DEFAULT 0       NULL,
    accepted    BOOLEAN,
    accepted_at DATETIME,
    created_at  DATETIME                NOT NULL,
    CONSTRAINT fk_user_circle_link_ref_circle_id FOREIGN KEY (circle_id) REFERENCES learning_circle (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_circle_link_ref_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE user_referral_link
(
    id          VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id     VARCHAR(36)             NOT NULL,
    referral_id VARCHAR(36)             NOT NULL,
    is_coin     BOOLEAN                 NOT NULL,
    updated_by  VARCHAR(36)             NOT NULL,
    updated_at  DATETIME                NOT NULL,
    created_by  VARCHAR(36)             NOT NULL,
    created_at  DATETIME                NOT NULL,
    CONSTRAINT fk_user_referral_link_ref_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_referral_link_referral_id FOREIGN KEY (referral_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_referral_link_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_referral_link_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE notification
(
    id          VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id     VARCHAR(36)             NOT NULL,
    title       VARCHAR(50)             NOT NULL,
    description VARCHAR(200)            NOT NULL,
    button      VARCHAR(10),
    url         VARCHAR(100),
    created_at  DATETIME                NOT NULL,
    created_by  VARCHAR(36)             NOT NULL,
    CONSTRAINT `fk_notification_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_notification_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE `device`
(
    `id`          VARCHAR(36) PRIMARY KEY NOT NULL,
    `browser`     VARCHAR(36)             NOT NULL,
    `os`          VARCHAR(36)             NOT NULL,
    `user_id`     VARCHAR(36)             NOT NULL,
    `last_log_in` DATETIME                NOT NULL,
    CONSTRAINT `fk_device_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE voucher_log
(
    id          VARCHAR(36) PRIMARY KEY NOT NULL,
    code        VARCHAR(15)             NOT NULL,
    user_id     VARCHAR(36)             NOT NULL,
    task_id     VARCHAR(36)             NOT NULL,
    karma       INT DEFAULT 0           NOT NULL,
    mail        VARCHAR(200)            NOT NULL,
    week        VARCHAR(2)              NULL,
    month       VARCHAR(10)             NOT NULL,
    claimed     BOOLEAN                 NOT NULL,
    event       VARCHAR(50)             NULL,
    description VARCHAR(2000)           NULL,
    updated_by  VARCHAR(36)             NOT NULL,
    updated_at  DATETIME                NOT NULL,
    created_by  VARCHAR(36)             NOT NULL,
    created_at  DATETIME                NOT NULL,
    CONSTRAINT fk_voucher_log_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_voucher_log_ref_task_id FOREIGN KEY (task_id) REFERENCES task_list (id) ON DELETE CASCADE,
    CONSTRAINT fk_voucher_log_ref_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE dynamic_role
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    type       VARCHAR(50)             NOT NULL,
    role       VARCHAR(36)             NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at datetime                NOT NULL,
    created_by varchar(36)             NOT NULL,
    created_at datetime                NOT NULL,
    CONSTRAINT fk_dynamic_role_ref_role_id FOREIGN KEY (role) REFERENCES role (id) ON DELETE CASCADE,
    CONSTRAINT fk_role_management_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_role_management_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE dynamic_user
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    type       VARCHAR(50)             NOT NULL,
    user_id    VARCHAR(36)             NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at datetime                NOT NULL,
    created_by varchar(36)             NOT NULL,
    created_at datetime                NOT NULL,
    CONSTRAINT fk_dynamic_user_ref_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_dynamic_user_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_dynamic_user_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE mucoin_invite_log
(
    id          VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id     VARCHAR(36)             NOT NULL,
    email       VARCHAR(200)            NOT NULL,
    invite_code VARCHAR(36)             NOT NULL,
    created_by  VARCHAR(36)             NOT NULL,
    created_at  DATETIME                NOT NULL,
    CONSTRAINT fk_mucoin_invite_log_ref_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_mucoin_invite_log_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE mucoin_activity_log
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id    VARCHAR(36)             NOT NULL,
    coin       FLOAT                   NOT NULL,
    status     VARCHAR(36)             NOT NULL,
    task_id    VARCHAR(36)             NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT fk_mucoin_activity_log_ref_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_mucoin_activity_log_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_mucoin_activity_log_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_mucoin_activity_log_ref_task_id FOREIGN KEY (task_id) REFERENCES task_list (id) ON DELETE CASCADE
);

CREATE TABLE intro_task_log
(
    id         VARCHAR(36) NOT NULL PRIMARY KEY,
    user_id    VARCHAR(36) NOT NULL,
    progress   INT         NOT NULL,
    channel_id VARCHAR(36) NULL,
    updated_by VARCHAR(36) NOT NULL,
    updated_at DATETIME    NOT NULL,
    created_by VARCHAR(36) NOT NULL,
    created_at DATETIME    NOT NULL,
    CONSTRAINT fk_intro_task_log_ref_created_by
        FOREIGN KEY (created_by) REFERENCES user (id)
            ON DELETE CASCADE,
    CONSTRAINT fk_intro_task_log_ref_updated_by
        FOREIGN KEY (updated_by) REFERENCES user (id)
            ON DELETE CASCADE,
    CONSTRAINT fk_intro_task_log_ref_user_id
        FOREIGN KEY (user_id) REFERENCES user (id)
            ON DELETE CASCADE
);

CREATE TABLE org_karma_type
(
    id          VARCHAR(36) PRIMARY KEY NOT NULL,
    title       VARCHAR(75)             NOT NULL,
    karma       INTEGER DEFAULT 0       NOT NULL,
    description VARCHAR(200),
    updated_by  VARCHAR(36)             NOT NULL,
    updated_at  DATETIME                NOT NULL,
    created_by  VARCHAR(36)             NOT NULL,
    created_at  DATETIME                NOT NULL,
    CONSTRAINT `fk_org_karma_type_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_org_karma_type_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE org_karma_log
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    org_id     VARCHAR(36)             NOT NULL,
    karma      INTEGER DEFAULT 0       NOT NULL,
    type       VARCHAR(36)             NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT fk_org_karma_log_ref_org_id FOREIGN KEY (org_id) REFERENCES organization (id) ON DELETE CASCADE,
    CONSTRAINT fk_org_karma_log_ref_type FOREIGN KEY (`type`) REFERENCES `org_karma_type` (`id`) ON DELETE CASCADE,
    CONSTRAINT fk_org_karma_log_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_org_karma_log_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE login_attempts_log
(
    id          VARCHAR(36) PRIMARY KEY NOT NULL,
    email_muid  VARCHAR(200)            NOT NULL,
    status      VARCHAR(36)             NOT NULL,
    type        VARCHAR(36)             NOT NULL,
    ip_address  VARCHAR(45),
    browser     VARCHAR(255),
    os          VARCHAR(255),
    version     VARCHAR(255),
    device_type VARCHAR(255),
    city        VARCHAR(36),
    region      VARCHAR(36),
    country     VARCHAR(36),
    location    VARCHAR(36),
    created_at  DATETIME                NOT NULL
);

-- events: recreated per alter-1.80.sql (new design). The pre-1.80 design
-- (id, name, description, updated_by, updated_at, created_by, created_at)
-- is superseded; production keeps the old data via a rename to
-- events_old_backup before creating this new table. NOTE: the `name`
-- column from the old design has no direct equivalent below (replaced by
-- `title` + `slug`) -- flagged in the alter-1.80 report, not silently dropped.
-- fk_events_category (-> categories) is added later via ALTER, after the
-- `categories` table is created further down in this file.
CREATE TABLE `events` (
  `id` varchar(36) NOT NULL,
  `title` varchar(200) NOT NULL,
  `slug` varchar(255) DEFAULT NULL,
  `description` text,
  `ig_id` varchar(36) DEFAULT NULL,
  `mentor_review_status` enum('PENDING','APPROVED','REJECTED') NOT NULL DEFAULT 'PENDING',
  `reviewed_by` varchar(36) DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `review_feedback` varchar(500) DEFAULT NULL,
  `cover_image` varchar(512) DEFAULT NULL,
  `banner_image` varchar(512) DEFAULT NULL,
  `category_id` varchar(36) DEFAULT NULL,
  `status` enum('draft','pending_campus_approval','pending_approval','pending_mentor_approval','published','ongoing','completed','cancelled','rejected') NOT NULL DEFAULT 'draft',
  `start_datetime` datetime NOT NULL,
  `end_datetime` datetime NOT NULL,
  `registration_url` varchar(500) DEFAULT NULL,
  `registration_deadline` datetime DEFAULT NULL,
  `min_karma` bigint unsigned DEFAULT NULL,
  `venue_type` enum('physical','online','hybrid') NOT NULL DEFAULT 'online',
  `venue_address` varchar(300) DEFAULT NULL,
  `venue_maps_url` varchar(500) DEFAULT NULL,
  `venue_online_link` varchar(500) DEFAULT NULL,
  `venue_platform` varchar(100) DEFAULT NULL,
  `scope` enum('global','campus','ig','campus_ig','company') NOT NULL DEFAULT 'global',
  `scope_org_id` varchar(36) DEFAULT NULL,
  `scope_ig_id` varchar(36) DEFAULT NULL,
  `scope_ci_id` varchar(36) DEFAULT NULL,
  `event_type` ENUM('hackathon', 'workshop', 'webinar', 'seminar', 'bootcamp', 'meetup', 'conference', 'competition', 'ideathon', 'cultural_event', 'sports_event', 'community_event', 'expo', 'networking_event', 'tech_talk', 'others') NOT NULL DEFAULT 'others',
  `organiser_type` enum('global_ig','campus_ig','campus','company','admin','partner') NOT NULL,
  `organiser_ig_id` varchar(36) DEFAULT NULL,
  `organiser_org_id` varchar(36) DEFAULT NULL,
  `organiser_ci_id` varchar(36) DEFAULT NULL,
  `event_scope` enum('maker','coder','manager','creative') NOT NULL DEFAULT 'coder',
  `is_featured` tinyint(1) NOT NULL DEFAULT '0',
  `is_collaboration` tinyint(1) NOT NULL DEFAULT '0',
  `interest_count` int unsigned NOT NULL DEFAULT '0',
  `tags` json DEFAULT NULL,
  `user_limit` int unsigned NOT NULL DEFAULT '0',
  `created_by` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `venue_city` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_events_slug` (`slug`),
  KEY `fk_events_category` (`category_id`),
  KEY `fk_events_created` (`created_by`),
  KEY `fk_events_updated` (`updated_by`),
  KEY `idx_events_org_org` (`organiser_org_id`),
  KEY `idx_events_status_start` (`status`,`start_datetime`),
  KEY `idx_events_status_end` (`status`,`end_datetime`),
  KEY `idx_events_deleted_at` (`deleted_at`),
  KEY `idx_events_featured` (`is_featured`,`status`),
  KEY `idx_events_scope` (`scope`),
  KEY `idx_events_scope_org` (`scope_org_id`),
  KEY `idx_events_scope_ig` (`scope_ig_id`),
  KEY `idx_events_org_ig` (`organiser_ig_id`),
  KEY `idx_events_review` (`ig_id`,`mentor_review_status`),
  KEY `fk_events_ref_reviewed_by` (`reviewed_by`),
  CONSTRAINT `fk_events_created` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_events_org_ig` FOREIGN KEY (`organiser_ig_id`) REFERENCES `interest_group` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_events_org_org` FOREIGN KEY (`organiser_org_id`) REFERENCES `organization` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_events_ref_ig` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_events_ref_reviewed_by` FOREIGN KEY (`reviewed_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_events_scope_ig` FOREIGN KEY (`scope_ig_id`) REFERENCES `interest_group` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_events_scope_org` FOREIGN KEY (`scope_org_id`) REFERENCES `organization` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_events_updated` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `chk_events_dates` CHECK ((`end_datetime` > `start_datetime`)),
  CONSTRAINT `chk_events_karma` CHECK (((`min_karma` is null) or (`min_karma` >= 0)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE orgbot_channel
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    name       VARCHAR(75)             NOT NULL,
    discord_id VARCHAR(36)             NOT NULL,
    org_id     VARCHAR(36)             NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT fk_orgbot_channel_ref_org_id FOREIGN KEY (org_id) REFERENCES organization (id) ON DELETE CASCADE,
    CONSTRAINT fk_orgbot_channel_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_orgbot_channel_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE orgbot_tasks
(
    id          VARCHAR(36) PRIMARY KEY NOT NULL,
    title       VARCHAR(75)             NOT NULL,
    hashtag     VARCHAR(75)             NOT NULL,
    description VARCHAR(200)            NOT NULL,
    org_id      VARCHAR(36)             NOT NULL,
    karma       INTEGER,
    usage_count INTEGER,
    level_order INTEGER DEFAULT NULL,
    channel_id  VARCHAR(36),
    updated_by  VARCHAR(36)             NOT NULL,
    updated_at  DATETIME                NOT NULL,
    created_by  VARCHAR(36)             NOT NULL,
    created_at  DATETIME                NOT NULL,
    CONSTRAINT fk_orgbot_tasks_ref_channel_id FOREIGN KEY (channel_id) REFERENCES orgbot_channel (id) ON DELETE CASCADE,
    CONSTRAINT fk_orgbot_tasks_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_orgbot_tasks_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE orgbot_karma_log
(
    id                    VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id               VARCHAR(36)             NOT NULL,
    karma                 INTEGER     DEFAULT 0   NOT NULL,
    task_id               VARCHAR(36)             NOT NULL,
    task_message_id       VARCHAR(36)             NULL,
    lobby_message_id      VARCHAR(36),
    dm_message_id         VARCHAR(36),
    peer_approved         BOOLEAN,
    peer_approved_by      VARCHAR(36),
    appraiser_approved    BOOLEAN,
    appraiser_approved_by VARCHAR(36),
    updated_by            VARCHAR(36)             NOT NULL,
    updated_at            DATETIME                NOT NULL,
    created_by            VARCHAR(36)             NOT NULL,
    created_at            DATETIME                NOT NULL,
    CONSTRAINT fk_orgbot_karma_log_ref_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_orgbot_karma_log_ref_task_id FOREIGN KEY (task_id) REFERENCES orgbot_tasks (id) ON DELETE CASCADE,
    CONSTRAINT fk_orgbot_karma_log_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_orgbot_karma_log_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE user_mentor
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id    VARCHAR(36)             NOT NULL,
    about      VARCHAR(1000)           NULL,
    reason     VARCHAR(1000)           NULL,
    hours      INT                     NOT NULL,
    updated_by VARCHAR(36)             NOT NULL,
    updated_at DATETIME                NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NULL,
    CONSTRAINT fk_user_mentor_ref_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_mentor_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_mentor_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE user_coupon_link
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id    VARCHAR(75)             NOT NULL,
    coupon     VARCHAR(15)             NOT NULL,
    type       VARCHAR(36)             NOT NULL,
    created_by VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,
    CONSTRAINT fk_user_coupon_link_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_coupon_link_ref_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE donor
(
    id             VARCHAR(36)   PRIMARY KEY  NOT NULL,
    payment_id     VARCHAR(100)               NOT NULL,
    payment_method VARCHAR(100)               NOT NULL,
    amount         FLOAT                      NOT NULL,
    currency       VARCHAR(30)                NOT NULL,
    name           VARCHAR(100)               NOT NULL,
    email          VARCHAR(200)               NOT NULL,
    company        VARCHAR(100),                       
    phone_number   VARCHAR(20),
    pan_number     VARCHAR(10),
    created_by     VARCHAR(36)                NOT NULL,
    created_at     DATETIME                   NOT NULL,
    CONSTRAINT fk_donor_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE launchpad_user
(
    id            VARCHAR(36)  PRIMARY KEY NOT NULL,
    email         VARCHAR(255) UNIQUE      NOT NULL,
    phone_number  VARCHAR(15),
    full_name     VARCHAR(255),
    district      VARCHAR(100),
    zone          VARCHAR(100),
    role          VARCHAR(20)              NOT NULL,
    created_at    DATETIME                 NOT NULL,
    updated_at    DATETIME                 NOT NULL
);

CREATE TABLE launchpad_user_college_link
(
    id            VARCHAR(36)  PRIMARY KEY NOT NULL,
    user_id       VARCHAR(36)               NOT NULL,
    college_id    VARCHAR(36)               NOT NULL,
    created_at    DATETIME                  NOT NULL,
    updated_at    DATETIME                  NOT NULL,
    created_by_id VARCHAR(36)               NOT NULL,
    updated_by_id VARCHAR(36)               NOT NULL,
    CONSTRAINT fk_launchpad_user_college_link_user_id FOREIGN KEY (user_id) REFERENCES launchpad_user(id) ON DELETE CASCADE,
    CONSTRAINT fk_launchpad_user_college_link_college_id FOREIGN KEY (college_id) REFERENCES organization(id) ON DELETE CASCADE,
    CONSTRAINT fk_launchpad_user_college_link_created_by_id FOREIGN KEY (created_by_id) REFERENCES launchpad_user(id) ON DELETE CASCADE,
    CONSTRAINT fk_launchpad_user_college_link_updated_by_id FOREIGN KEY (updated_by_id) REFERENCES launchpad_user(id) ON DELETE CASCADE
);

CREATE TABLE launchpad
(
    id            VARCHAR(36)  PRIMARY KEY NOT NULL,
    user_id       VARCHAR(36)               NOT NULL,
    launchpad_id  VARCHAR(100) UNIQUE       NOT NULL,
    created_at    DATETIME                  NOT NULL,
    updated_at    DATETIME                  NOT NULL,
    created_by VARCHAR(36)               NOT NULL,
    updated_by VARCHAR(36)               NOT NULL,
    CONSTRAINT fk_launchpad_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_launchpad_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_launchpad_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE user_domains (
	id          VARCHAR(36)     PRIMARY KEY,
	user_id     VARCHAR(36)     NOT NULL,
	domain_name VARCHAR(100)    NOT NULL,
	created_at  DATETIME        NOT NULL,
	updated_at  DATETIME        NOT NULL,
	CONSTRAINT `fk_user_domains_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
);

CREATE TABLE user_endgoals (
	id              VARCHAR(36)     PRIMARY KEY,
	user_id         VARCHAR(36)     NOT NULL,
	endgoal_name    VARCHAR(100)    NOT NULL,
	created_at      DATETIME        NOT NULL,
	updated_at      DATETIME        NOT NULL,
	CONSTRAINT `fk_user_endgoals_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
);


CREATE TABLE unverified_organization (
	id                VARCHAR(36) PRIMARY KEY NOT NULL,
	title			  VARCHAR(100) NOT NULL,
	org_type 		  VARCHAR(25) NOT NULL,
    graduation_year   INT NULL,
    department_id     VARCHAR(36) NULL,
	verified 		  BOOLEAN,
	verified_by 	  VARCHAR(36),
	verified_at		  DATETIME,
	org_id			  VARCHAR(36),
	created_by        VARCHAR(36) NOT NULL,
	created_at		  DATETIME NOT NULL,
    CONSTRAINT fk_unverified_organizations_verified_by_user FOREIGN KEY (verified_by) REFERENCES user (id) ON DELETE NO ACTION,
    CONSTRAINT fk_unverified_organizations_org_id_organization FOREIGN KEY (org_id) REFERENCES organization (id) ON DELETE NO ACTION,
    CONSTRAINT fk_unverified_organizations_department_id_department FOREIGN KEY (department_id) REFERENCES department (id) ON DELETE NO ACTION,
	CONSTRAINT fk_unverified_organizations_created_by_user FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE
);

ALTER TABLE user
    ADD COLUMN district_id VARCHAR(36);

ALTER TABLE user
    ADD CONSTRAINT fk_user_ref_district_id FOREIGN KEY (district_id) REFERENCES district (id) ON DELETE CASCADE;


CREATE TABLE achievement
(
    id               VARCHAR(36)   PRIMARY KEY      NOT NULL,
    name             VARCHAR(75)   UNIQUE           NOT NULL,
    level_id         VARCHAR(36)                    DEFAULT NULL,
    description      VARCHAR(300)                   NOT NULL,
    icon             VARCHAR(100)                   DEFAULT NULL,
    has_vc           BOOLEAN       DEFAULT FALSE    NOT NULL,
    tags             JSON                           NOT NULL,
    type             VARCHAR(36)                    NOT NULL,
    updated_by       VARCHAR(36)                    NOT NULL,
    updated_at       DATETIME                       NOT NULL,
    created_by       VARCHAR(36)                    NOT NULL,
    created_at       DATETIME                       NOT NULL,
    template_id      VARCHAR(100)               DEFAULT NULL,
    CONSTRAINT `fk_achievement_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_achievement_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_achievement_ref_level` FOREIGN KEY (`level_id`) REFERENCES `level` (`id`) ON DELETE SET NULL
);

CREATE TABLE user_achievements_log
(
    id              VARCHAR(36)  PRIMARY KEY NOT NULL,
    user_id         VARCHAR(36)              NOT NULL,
    achievement_id  VARCHAR(36)              NOT NULL,
    is_issued       BOOLEAN DEFAULT FALSE    NOT NULL,
    vc_url          VARCHAR(100)                     ,
    updated_by      VARCHAR(36)              NOT NULL,
    updated_at      DATETIME                 NOT NULL,
    created_by      VARCHAR(36)              NOT NULL,
    created_at      DATETIME                 NOT NULL,
    CONSTRAINT `fk_user_achievements_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_achievements_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_achievements_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_achievements_achievement_id` FOREIGN KEY (`achievement_id`) REFERENCES `achievement` (`id`) ON DELETE CASCADE
);


CREATE TABLE launchpad_companies(
    id              VARCHAR(36) PRIMARY KEY NOT NULL,
    name            VARCHAR(100) UNIQUE NOT NULL,
    poc_name        VARCHAR(100) NOT NULL,
    poc_role        VARCHAR(100) NOT NULL,
    poc_email       VARCHAR(100) NOT NULL,
    poc_phone       VARCHAR(20)  NOT NULL,
    username        VARCHAR(50)  UNIQUE NOT NULL,
    password        VARCHAR(255) NOT NULL,
    created_at      DATETIME     NOT NULL,
    updated_at      DATETIME     NOT NULL
);

CREATE TABLE  launchpad_recruiters (
    id              VARCHAR(36) PRIMARY KEY NOT NULL,
    company_id      VARCHAR(36) NOT NULL,
    name            VARCHAR(100) NOT NULL,
    email           VARCHAR(100) UNIQUE NOT NULL,
    phone           VARCHAR(20)  NOT NULL,
    password        VARCHAR(255) NOT NULL,
    role            VARCHAR(50),
    created_at      DATETIME     NOT NULL,
    updated_at      DATETIME     NOT NULL,
    CONSTRAINT fk_launchpad_recruiters_company_id FOREIGN KEY (company_id) REFERENCES launchpad_companies(id) ON DELETE CASCADE
);

CREATE TABLE launchpad_jobs(
    id              VARCHAR(36) PRIMARY KEY NOT NULL,
    company_id      VARCHAR(36) NOT NULL,
    recruiter_id    VARCHAR(36) NOT NULL,
    title           VARCHAR(100) NOT NULL,
    skills          VARCHAR(255) ,
    experience      VARCHAR(255) ,
    domain          VARCHAR(255) NOT NULL,
    interest_groups VARCHAR(255) NOT NULL,
    task_description TEXT ,
    created_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL,
    CONSTRAINT fk_launchpad_jobs_company_id FOREIGN KEY (company_id) REFERENCES launchpad_companies(id) ON DELETE CASCADE,
    CONSTRAINT fk_launchpad_jobs_recruiter_id FOREIGN KEY (recruiter_id) REFERENCES launchpad_recruiters(id) ON DELETE CASCADE
);

ALTER TABLE launchpad_companies
    ADD COLUMN is_verified BOOLEAN DEFAULT FALSE AFTER password;

CREATE TABLE quiz (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    pass_rate INT DEFAULT 70,
    ordered BOOLEAN DEFAULT FALSE,
    name_long TEXT
);

CREATE TABLE quiz_sessions (
    id VARCHAR(36) PRIMARY KEY,
    discord_id VARCHAR(32) NOT NULL,
    channel_id VARCHAR(32) NOT NULL,
    current_question CHAR(36) DEFAULT NULL,
    active BOOLEAN DEFAULT TRUE,
    passed BOOLEAN DEFAULT FALSE,
    quiz_id CHAR(36) NOT NULL,
    FOREIGN KEY (quiz_id) REFERENCES quiz(id) ON DELETE CASCADE
);

CREATE TABLE quiz_questions (
    id VARCHAR(36) PRIMARY KEY,
    quiz_id CHAR(36) NOT NULL,
    question TEXT NOT NULL,
    order_num INT,
    FOREIGN KEY (quiz_id) REFERENCES quiz(id) ON DELETE CASCADE
);

CREATE TABLE quiz_answers (
    id VARCHAR(36) PRIMARY KEY,
    question_id CHAR(36) NOT NULL,
    answer TEXT NOT NULL,
    is_correct BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (question_id) REFERENCES quiz_questions(id) ON DELETE CASCADE
);

CREATE TABLE quiz_log (
    id VARCHAR(36) PRIMARY KEY,
    discord_id VARCHAR(32) NOT NULL,
    quiz_id CHAR(36) NOT NULL,
    attempt INT DEFAULT 1,
    passed BOOLEAN DEFAULT FALSE,
    score INT,
    attempted_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (quiz_id) REFERENCES quiz(id) ON DELETE CASCADE
);

CREATE TABLE donation (
    id VARCHAR(36) PRIMARY KEY,
    donor_id VARCHAR(36) NOT NULL,
    order_id VARCHAR(100) NULL,
    payment_id VARCHAR(100) NULL,
    payment_method VARCHAR(50) NULL,
    amount DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    donation_type VARCHAR(20) NOT NULL,
    is_paid BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_donation_donor FOREIGN KEY (donor_id) REFERENCES donor(id)
);

ALTER TABLE launchpad_companies
ADD COLUMN website VARCHAR(200) NULL AFTER name;

ALTER TABLE launchpad_companies
ADD COLUMN description TEXT NULL AFTER website;

ALTER TABLE launchpad_companies
ADD COLUMN address VARCHAR(255) NULL AFTER description;

CREATE TABLE launchpad_job_tasks (
    id                  VARCHAR(36)     PRIMARY KEY,
    task_description    TEXT            NOT NULL,
    hashtags            VARCHAR(255),
    is_verified         BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

ALTER TABLE launchpad_jobs
ADD COLUMN opening_type VARCHAR(50) NULL,
ADD COLUMN location VARCHAR(255) NULL,
ADD COLUMN salary_range VARCHAR(50) NULL,
ADD COLUMN job_type VARCHAR(50) NULL,
ADD COLUMN minimum_karma INT DEFAULT 0 NULL,
ADD COLUMN task_id VARCHAR(36);

ALTER TABLE launchpad_jobs
ADD CONSTRAINT fk_launchpad_jobs_task
FOREIGN KEY (task_id) REFERENCES launchpad_job_tasks(id)
ON DELETE CASCADE;

CREATE TABLE launchpad_job_applications (
    id VARCHAR(36) PRIMARY KEY,

    job_id VARCHAR(36) NOT NULL,
    student_id VARCHAR(36) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'invited',

    resume_link VARCHAR(500),
    linkedin_link VARCHAR(500),
    portfolio_link VARCHAR(500),
    cover_letter TEXT,
    other_link VARCHAR(500),

    invited_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    applied_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uniq_job_student (job_id, student_id),

    CONSTRAINT fk_job FOREIGN KEY (job_id)
        REFERENCES launchpad_jobs(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_student FOREIGN KEY (student_id)
        REFERENCES user(id)
        ON DELETE CASCADE
);

ALTER TABLE launchpad_job_applications
ADD COLUMN interview_date DATETIME NULL AFTER other_link,
ADD COLUMN interview_time TIME NULL AFTER interview_date,
ADD COLUMN interview_platform VARCHAR(255) NULL AFTER interview_time,
ADD COLUMN interview_link VARCHAR(500) NULL AFTER interview_platform,
ADD COLUMN interview_type VARCHAR(100) NULL AFTER interview_link;


ALTER TABLE circle_meeting_log
ADD COLUMN is_recurring BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN recurrence_type VARCHAR(10) NULL DEFAULT NULL,
ADD COLUMN recurrence INT NULL DEFAULT NULL;


UPDATE circle_meeting_log AS cml
JOIN learning_circle AS lc ON cml.circle_id = lc.id
JOIN (
    SELECT circle_id, MAX(created_at) AS max_created_at
    FROM circle_meeting_log
    GROUP BY circle_id
) AS latest_meeting
  ON cml.circle_id = latest_meeting.circle_id
 AND cml.created_at = latest_meeting.max_created_at
SET
  cml.is_recurring = lc.is_recurring,
  cml.recurrence_type = lc.recurrence_type,
  cml.recurrence = lc.recurrence
WHERE
  lc.is_recurring = TRUE;


ALTER TABLE learning_circle
DROP COLUMN is_recurring,
DROP COLUMN recurrence_type,
DROP COLUMN recurrence;

ALTER TABLE task_list 
MODIFY description TEXT;

ALTER TABLE launchpad_companies
ADD COLUMN reset_token VARCHAR(100) NULL,
ADD COLUMN reset_token_expires TIMESTAMP NULL;

ALTER TABLE launchpad_recruiters
ADD COLUMN reset_token VARCHAR(100) NULL,
ADD COLUMN reset_token_expires TIMESTAMP NULL;

CREATE INDEX idx_launchpad_companies_reset_token ON launchpad_companies(reset_token);
CREATE INDEX idx_launchpad_recruiters_reset_token ON launchpad_recruiters(reset_token);

ALTER TABLE donor ADD COLUMN address TEXT NULL;
ALTER TABLE donor ADD COLUMN is_organisation BOOLEAN DEFAULT FALSE;
ALTER TABLE donation ADD COLUMN donation_name VARCHAR(100) NULL;

CREATE INDEX idx_donation_donor_id ON donation(donor_id);
CREATE INDEX idx_donation_order_id ON donation(order_id);
CREATE INDEX idx_donor_email ON donor(email);

-- Bank transfer fields for donations >= 5L
ALTER TABLE donation ADD COLUMN payment_status VARCHAR(30) DEFAULT 'COMPLETED';
ALTER TABLE donation ADD COLUMN reference_code VARCHAR(50);
ALTER TABLE donation ADD COLUMN proof_url TEXT;

CREATE INDEX idx_donation_reference_code ON donation(reference_code);
CREATE INDEX idx_donation_payment_status ON donation(payment_status);


ALTER TABLE interest_group 
ADD COLUMN about TEXT NULL, 
ADD COLUMN prerequisites TEXT NULL, 
ADD COLUMN resource TEXT NULL, 
ADD COLUMN career_opportunities TEXT NULL, 
ADD COLUMN top_blogs TEXT NULL, 
ADD COLUMN people_to_follow TEXT NULL, 
ADD COLUMN leads TEXT NULL, 
ADD COLUMN mentors TEXT NULL, 
ADD COLUMN thinktank TEXT NULL, 
ADD COLUMN office_hours VARCHAR(200) NULL;


CREATE TABLE `task_report` (
  `id` varchar(36) NOT NULL,
  `reporter_id` varchar(36) NOT NULL,
  `offender_id` varchar(36) NOT NULL,
  `message_id` varchar(100) NOT NULL, -- Discord Message ID
  `reason` varchar(500) NOT NULL,
  `proof_link` varchar(255) DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'PENDING', -- PENDING, RESOLVED, REJECTED
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_task_report_ref_reporter_id` (`reporter_id`),
  KEY `fk_task_report_ref_offender_id` (`offender_id`),
  KEY `fk_task_report_ref_created_by` (`created_by`),
  KEY `fk_task_report_ref_updated_by` (`updated_by`),
  CONSTRAINT `fk_task_report_ref_reporter_id` FOREIGN KEY (`reporter_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_report_ref_offender_id` FOREIGN KEY (`offender_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_report_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_report_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `jobs` (
  `id` varchar(36) NOT NULL,
  `type` varchar(255) NOT NULL,
  `target_url` varchar(255) NOT NULL,
  `target_method` varchar(255) NOT NULL,
  `headers` json DEFAULT NULL,
  `params` json DEFAULT NULL,
  `payload` json DEFAULT NULL,
  `body` json DEFAULT NULL,
  `scheduling` json DEFAULT NULL,
  `retries` json DEFAULT NULL,
  `status` varchar(255) NOT NULL DEFAULT 'scheduled',
  `attempt_count` int NOT NULL DEFAULT '0',
  `last_error` text,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE IF NOT EXISTS achievement_event (
    id              VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id        VARCHAR(36) NOT NULL,
    event_type      VARCHAR(50) NOT NULL,
    user_id         VARCHAR(36) NOT NULL,
    region          VARCHAR(50),
    metadata        JSON NOT NULL,
    processed       BOOLEAN DEFAULT FALSE,
    created_at      DATETIME NOT NULL,
    UNIQUE KEY uk_event_id (event_id),
    INDEX idx_event_user (user_id),
    INDEX idx_event_type (event_type),
    INDEX idx_event_processed (processed),
    CONSTRAINT fk_achievement_event_user FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

-- Achievement Rules (versioned, JSON-based conditions)
CREATE TABLE IF NOT EXISTS achievement_rule (
    id              VARCHAR(36) PRIMARY KEY NOT NULL,
    achievement_id  VARCHAR(36) NOT NULL,
    version         INT NOT NULL DEFAULT 1,
    rule_type       VARCHAR(30) NOT NULL,
    conditions      JSON NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    created_by      VARCHAR(36) NOT NULL,
    created_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL,
    INDEX idx_rule_achievement (achievement_id),
    INDEX idx_rule_active (is_active),
    UNIQUE KEY uk_achievement_version (achievement_id, version),
    CONSTRAINT fk_rule_achievement FOREIGN KEY (achievement_id) REFERENCES achievement(id) ON DELETE CASCADE,
    CONSTRAINT fk_rule_created_by FOREIGN KEY (created_by) REFERENCES user(id) ON DELETE CASCADE
);

-- User Skill Progress (pre-aggregated for O(1) eligibility checks)
CREATE TABLE IF NOT EXISTS user_skill_progress (
    id                      VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id                 VARCHAR(36) NOT NULL,
    skill_id                VARCHAR(36) NOT NULL,
    completed_task_count    INT DEFAULT 0,
    total_karma             INT DEFAULT 0,
    last_task_at            DATETIME,
    created_at              DATETIME NOT NULL,
    updated_at              DATETIME NOT NULL,
    UNIQUE KEY uk_user_skill (user_id, skill_id),
    INDEX idx_skill_user (user_id),
    CONSTRAINT fk_skill_progress_user FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

-- User IG Karma (pre-aggregated karma per user+IG combination)
CREATE TABLE IF NOT EXISTS user_ig_karma (
    id              VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id         VARCHAR(36) NOT NULL,
    ig_id           VARCHAR(36) NOT NULL,
    total_karma     INT DEFAULT 0,
    task_count      INT DEFAULT 0,
    last_activity   DATETIME,
    created_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL,
    UNIQUE KEY uk_user_ig (user_id, ig_id),
    INDEX idx_ig_karma_user (user_id),
    INDEX idx_ig_karma_ig (ig_id),
    CONSTRAINT fk_ig_karma_user FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    CONSTRAINT fk_ig_karma_ig FOREIGN KEY (ig_id) REFERENCES interest_group(id) ON DELETE CASCADE
);

-- User Daily Activity (source of truth for streak calculation)
CREATE TABLE IF NOT EXISTS user_daily_activity (
    id              VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id         VARCHAR(36) NOT NULL,
    activity_date   DATE NOT NULL,
    has_task        BOOLEAN DEFAULT FALSE,
    has_karma       BOOLEAN DEFAULT FALSE,
    has_login       BOOLEAN DEFAULT FALSE,
    task_count      INT DEFAULT 0,
    karma_earned    INT DEFAULT 0,
    created_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL,
    UNIQUE KEY uk_user_date (user_id, activity_date),
    INDEX idx_daily_user (user_id),
    INDEX idx_daily_date (activity_date),
    CONSTRAINT fk_daily_activity_user FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

-- User Streaks (derived from daily activity)
CREATE TABLE IF NOT EXISTS user_streak (
    id              VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id         VARCHAR(36) NOT NULL,
    streak_type     VARCHAR(30) NOT NULL,
    current_streak  INT DEFAULT 0,
    longest_streak  INT DEFAULT 0,
    last_active     DATE,
    created_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL,
    UNIQUE KEY uk_user_streak_type (user_id, streak_type),
    INDEX idx_streak_user (user_id),
    CONSTRAINT fk_streak_user FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

-- Achievement Audit Log (full audit trail for debugging and compliance)
CREATE TABLE IF NOT EXISTS achievement_audit_log (
    id              VARCHAR(36) PRIMARY KEY NOT NULL,
    user_id         VARCHAR(36) NOT NULL,
    achievement_id  VARCHAR(36) NOT NULL,
    action          VARCHAR(20) NOT NULL,
    rule_version    INT,
    metadata        JSON,
    performed_by    VARCHAR(36),
    created_at      DATETIME NOT NULL,
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_achievement (achievement_id),
    INDEX idx_audit_action (action),
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    CONSTRAINT fk_audit_achievement FOREIGN KEY (achievement_id) REFERENCES achievement(id) ON DELETE CASCADE
);

-- Add unique constraint to user_achievements_log for idempotency (prevents double-issue)
ALTER TABLE user_achievements_log 
ADD UNIQUE KEY uk_user_achievement (user_id, achievement_id);

-- Add rule_version column to user_achievements_log
ALTER TABLE user_achievements_log 
ADD COLUMN rule_version INT DEFAULT 1 AFTER achievement_id;

CREATE TABLE IF NOT EXISTS skill (
    id              VARCHAR(36) PRIMARY KEY NOT NULL,
    name            VARCHAR(75) NOT NULL,
    code            VARCHAR(20) NOT NULL,
    description     TEXT,
    icon            VARCHAR(100),
    is_active       BOOLEAN DEFAULT TRUE,
    created_by      VARCHAR(36) NOT NULL,
    created_at      DATETIME NOT NULL,
    updated_by      VARCHAR(36) NOT NULL,
    updated_at      DATETIME NOT NULL,
    UNIQUE KEY uk_skill_name (name),
    UNIQUE KEY uk_skill_code (code),
    INDEX idx_skill_active (is_active),
    CONSTRAINT fk_skill_created_by FOREIGN KEY (created_by) REFERENCES user(id) ON DELETE CASCADE,
    CONSTRAINT fk_skill_updated_by FOREIGN KEY (updated_by) REFERENCES user(id) ON DELETE CASCADE
);

-- Create task_skill_link junction table for many-to-many relationship
CREATE TABLE IF NOT EXISTS task_skill_link (
    id              VARCHAR(36) PRIMARY KEY NOT NULL,
    task_id         VARCHAR(36) NOT NULL,
    skill_id        VARCHAR(36) NOT NULL,
    created_by      VARCHAR(36) NOT NULL,
    created_at      DATETIME NOT NULL,
    UNIQUE KEY uk_task_skill (task_id, skill_id),
    INDEX idx_tsl_task (task_id),
    INDEX idx_tsl_skill (skill_id),
    CONSTRAINT fk_tsl_task FOREIGN KEY (task_id) REFERENCES task_list(id) ON DELETE CASCADE,
    CONSTRAINT fk_tsl_skill FOREIGN KEY (skill_id) REFERENCES skill(id) ON DELETE CASCADE,
    CONSTRAINT fk_tsl_created_by FOREIGN KEY (created_by) REFERENCES user(id) ON DELETE CASCADE
);

-- Add category and is_active fields to achievement table
ALTER TABLE achievement 
ADD COLUMN category VARCHAR(30) DEFAULT 'general' AFTER type,
ADD COLUMN is_active BOOLEAN DEFAULT TRUE AFTER category;

-- Add indexes for achievement filtering
CREATE INDEX idx_achievement_category ON achievement(category);
CREATE INDEX idx_achievement_is_active ON achievement(is_active);


CREATE TABLE IF NOT EXISTS `media_content` (
  `id`               VARCHAR(36)  NOT NULL PRIMARY KEY,
  `content_type`     VARCHAR(30)  NOT NULL,
  `title`            VARCHAR(300) NOT NULL,
  `date`             DATE         NOT NULL,
  `time`             TIME,
  `description`      TEXT,
  `link`             VARCHAR(500),
  `performer`        VARCHAR(200),
  `designation`      VARCHAR(200),
  `interest_groups`  JSON,
  `poster_thumbnail` VARCHAR(512),
  `campus`           VARCHAR(200),
  `zone`             VARCHAR(10),
  `created_by`       VARCHAR(36)  NOT NULL,
  `updated_by`       VARCHAR(36)  NOT NULL,
  `created_at`       DATETIME(6)  NOT NULL,
  `updated_at`       DATETIME(6)  NOT NULL,
  `deleted_at`       DATETIME(6),
  INDEX `idx_media_content_type` (`content_type`),
  INDEX `idx_media_content_date` (`date`),
  CONSTRAINT `fk_mc_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_mc_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`)
);


-- ============================================================================
-- alter-1.80.sql sync: new tables
-- ============================================================================

CREATE TABLE `level_system` (
  `id` varchar(36) NOT NULL,
  `name` varchar(36) NOT NULL,
  `type` varchar(36) NOT NULL,
  `description` text,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_level_system_ref_created_by` (`created_by`),
  KEY `fk_level_system_ref_updated_by` (`updated_by`),
  CONSTRAINT `fk_level_system_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_level_system_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `categories` (
  `id` varchar(36) NOT NULL,
  `name` varchar(255) NOT NULL,
  `description` text,
  `entity_id` varchar(36) NOT NULL,
  `entity_type` enum('event') NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_categories_entity` (`entity_id`,`entity_type`),
  KEY `fk_categorie_ref_created_by` (`created_by`),
  KEY `fk_categorie_ref_updated_by` (`updated_by`),
  CONSTRAINT `fk_categorie_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_categorie_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `my_cache_table` (
  `cache_key` varchar(255) NOT NULL,
  `value` longtext NOT NULL,
  `expires` datetime(6) NOT NULL,
  PRIMARY KEY (`cache_key`),
  KEY `my_cache_table_expires` (`expires`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `activity_point_certificate_log` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `level_id` varchar(36) NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_apcl_ref_user` (`user_id`),
  KEY `fk_apcl_ref_level` (`level_id`),
  KEY `fk_apcl_ref_created_by` (`created_by`),
  KEY `fk_apcl_ref_updated_by` (`updated_by`),
  CONSTRAINT `fk_apcl_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_apcl_ref_level` FOREIGN KEY (`level_id`) REFERENCES `level` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_apcl_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_apcl_ref_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `broadcast_notification` (
  `id` char(36) NOT NULL,
  `title` varchar(50) NOT NULL,
  `description` varchar(200) NOT NULL,
  `url` varchar(100) DEFAULT NULL,
  `target_type` enum('campus','interest_group','campus_ig','event_interest','event_coowners','global') NOT NULL,
  `target_id` char(36) DEFAULT NULL,
  `created_by` char(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `expires_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_broadcast_created_by` (`created_by`),
  CONSTRAINT `fk_broadcast_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- campus_ig_chapter includes icon_link (added by a later ALTER in alter-1.80.sql; baked in here)
CREATE TABLE `campus_ig_chapter` (
  `id` varchar(36) NOT NULL,
  `org_id` varchar(36) NOT NULL,
  `ig_id` varchar(36) NOT NULL,
  `lead_id` varchar(36) DEFAULT NULL,
  `description` text,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `icon_link` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_campus_ig` (`org_id`,`ig_id`),
  KEY `fk_cic_ig` (`ig_id`),
  KEY `fk_cic_lead` (`lead_id`),
  KEY `fk_cic_created_by` (`created_by`),
  KEY `fk_cic_updated_by` (`updated_by`),
  CONSTRAINT `fk_cic_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_cic_ig` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_cic_lead` FOREIGN KEY (`lead_id`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_cic_org` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_cic_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `campus_social_link` (
  `id` varchar(36) NOT NULL,
  `org_id` varchar(36) NOT NULL,
  `platform` varchar(20) NOT NULL,
  `url` varchar(500) NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_campus_platform` (`org_id`,`platform`),
  KEY `fk_csl_created_by` (`created_by`),
  KEY `fk_csl_updated_by` (`updated_by`),
  CONSTRAINT `fk_csl_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_csl_org` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_csl_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `channel_backup` (
  `id` varchar(36) NOT NULL,
  `name` varchar(75) NOT NULL,
  `discord_id` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `college_showcase` (
  `id` varchar(36) NOT NULL,
  `org_id` varchar(36) NOT NULL,
  `about` text,
  `hero_image` varchar(255) DEFAULT NULL,
  `highlights` json DEFAULT NULL,
  `gallery` json DEFAULT NULL,
  `testimonials` json DEFAULT NULL,
  `contact_email` varchar(255) DEFAULT NULL,
  `contact_phone` varchar(20) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `org_id` (`org_id`),
  KEY `created_by` (`created_by`),
  KEY `updated_by` (`updated_by`),
  CONSTRAINT `college_showcase_ibfk_1` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`) ON DELETE CASCADE,
  CONSTRAINT `college_showcase_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`),
  CONSTRAINT `college_showcase_ibfk_3` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `company` (
  `id` varchar(36) NOT NULL,
  `company_user_id` varchar(36) NOT NULL,
  `org_id` varchar(36) DEFAULT NULL,
  `name` varchar(75) NOT NULL,
  `logo` text,
  `description` text NOT NULL,
  `industry_sector` varchar(75) DEFAULT NULL,
  `website_link` text,
  `email` varchar(100) DEFAULT NULL,
  `slug` varchar(100) NOT NULL,
  `status` enum('pending','verified','rejected') DEFAULT 'pending',
  `location` varchar(150) DEFAULT NULL,
  `legal_name` varchar(150) DEFAULT NULL,
  `registration_number` varchar(100) DEFAULT NULL,
  `tax_id` varchar(100) DEFAULT NULL,
  `company_size` varchar(50) DEFAULT NULL,
  `linkedin_url` text,
  `verification_document_url` text,
  `verification_requested_at` datetime DEFAULT NULL,
  `verified_at` datetime DEFAULT NULL,
  `verified_by` varchar(36) DEFAULT NULL,
  `rejection_reason` text,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `updated_by` varchar(36) DEFAULT NULL,
  `deleted_by` varchar(36) DEFAULT NULL,
  `founded_year` smallint unsigned DEFAULT NULL,
  `remote_policy` varchar(20) DEFAULT NULL,
  `culture_text` text,
  `tech_stack` json DEFAULT NULL,
  `perks` json DEFAULT NULL,
  `testimonials` json DEFAULT NULL,
  `gallery` json DEFAULT NULL,
  `district_id` varchar(36) DEFAULT NULL,
  `state_id` varchar(36) DEFAULT NULL,
  `country_id` varchar(36) DEFAULT NULL,
  `short_pitch` varchar(900) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_company_name` (`name`),
  UNIQUE KEY `uniq_company_slug` (`slug`),
  UNIQUE KEY `uq_company_company_user_id` (`company_user_id`),
  KEY `fk_company_district` (`district_id`),
  KEY `fk_company_state` (`state_id`),
  KEY `fk_company_country` (`country_id`),
  KEY `fk_company_org` (`org_id`),
  CONSTRAINT `fk_company_country` FOREIGN KEY (`country_id`) REFERENCES `country` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_company_district` FOREIGN KEY (`district_id`) REFERENCES `district` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_company_state` FOREIGN KEY (`state_id`) REFERENCES `state` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_company_user` FOREIGN KEY (`company_user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_company_org` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `company_jobs` (
  `id` varchar(36) NOT NULL,
  `company_id` varchar(36) NOT NULL,
  `title` varchar(75) NOT NULL,
  `experience` varchar(20) DEFAULT NULL,
  `job_description` text,
  `location` varchar(75) DEFAULT NULL,
  `salary_range` varchar(36) DEFAULT NULL,
  `job_type` enum('Hybrid','Full-Time','Remote','Part-Time','Internship','Gig') NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `status` enum('Draft','Active','Closed','Expired') NOT NULL DEFAULT 'Draft',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0',
  `duration_value` smallint unsigned DEFAULT NULL COMMENT 'Numeric duration e.g. 3',
  `duration_unit` enum('days','weeks','months') DEFAULT NULL COMMENT 'Unit for duration field',
  `hourly_rate` decimal(10,2) DEFAULT NULL COMMENT 'Hourly pay rate for Gig jobs',
  `deliverables` json DEFAULT NULL COMMENT 'JSON array of deliverable strings for Gig jobs',
  `stipend` varchar(75) DEFAULT NULL COMMENT 'Monthly stipend for Internship jobs',
  `certificate_provided` enum('Yes','No') DEFAULT NULL COMMENT 'Yes or No for Internship',
  `total_views` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `fk_company_jobs` (`company_id`),
  CONSTRAINT `fk_company_jobs` FOREIGN KEY (`company_id`) REFERENCES `company` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `company_job_applications` (
  `id` varchar(36) NOT NULL,
  `job_id` varchar(36) NOT NULL,
  `applicant_id` varchar(36) NOT NULL,
  `status` varchar(15) NOT NULL DEFAULT 'applied',
  `cover_note` text,
  `reviewed_by` varchar(36) DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_job_applicant` (`job_id`,`applicant_id`),
  KEY `fk_cja_applicant` (`applicant_id`),
  KEY `fk_cja_reviewer` (`reviewed_by`),
  CONSTRAINT `fk_cja_applicant` FOREIGN KEY (`applicant_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_cja_job` FOREIGN KEY (`job_id`) REFERENCES `company_jobs` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_cja_reviewer` FOREIGN KEY (`reviewed_by`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `company_job_rules` (
  `id` varchar(36) NOT NULL,
  `job_id` varchar(36) NOT NULL,
  `rule_type` varchar(50) NOT NULL COMMENT 'e.g., min_karma, max_karma, min_level, max_level, skill, degree, interest_group, achievement, company_specific_task',
  `rule_value` varchar(150) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_job_rules_job` (`job_id`),
  CONSTRAINT `fk_job_rules_job` FOREIGN KEY (`job_id`) REFERENCES `company_jobs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `company_user_link` (
  `id` varchar(36) NOT NULL,
  `company_id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `role` varchar(20) NOT NULL DEFAULT 'employee' COMMENT 'employee | mentor',
  `status` varchar(20) NOT NULL DEFAULT 'active' COMMENT 'active | removed',
  `added_by` varchar(36) NOT NULL COMMENT 'user_id of the company admin who added this member',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_company_user` (`company_id`,`user_id`),
  KEY `user_id` (`user_id`),
  KEY `added_by` (`added_by`),
  CONSTRAINT `company_user_link_ibfk_1` FOREIGN KEY (`company_id`) REFERENCES `company` (`id`) ON DELETE CASCADE,
  CONSTRAINT `company_user_link_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `company_user_link_ibfk_3` FOREIGN KEY (`added_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `enabler_campus_note` (
  `id` varchar(36) NOT NULL,
  `enabler_id` varchar(36) NOT NULL,
  `campus_id` varchar(36) NOT NULL,
  `note` text NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `status` varchar(20) DEFAULT 'open',
  `priority` varchar(20) DEFAULT 'medium',
  `follow_up_date` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `enabler_id` (`enabler_id`),
  KEY `campus_id` (`campus_id`),
  KEY `created_by` (`created_by`),
  KEY `updated_by` (`updated_by`),
  CONSTRAINT `enabler_campus_note_ibfk_1` FOREIGN KEY (`enabler_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `enabler_campus_note_ibfk_2` FOREIGN KEY (`campus_id`) REFERENCES `organization` (`id`) ON DELETE CASCADE,
  CONSTRAINT `enabler_campus_note_ibfk_3` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`),
  CONSTRAINT `enabler_campus_note_ibfk_4` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `events_connection` (
  `id` varchar(36) NOT NULL,
  `event_id` varchar(36) NOT NULL,
  `entity_type` enum('user_ticket','co_owner','collab_ig','collab_campus','collab_campus_ig','collab_company','collab_partner') DEFAULT NULL,
  `entity_id` varchar(36) NOT NULL,
  `ticket_status` enum('pending','active','removed','rejected','withdrawn') DEFAULT NULL,
  `role_label` varchar(100) DEFAULT NULL,
  `invite_status` enum('pending','accepted','rejected') DEFAULT NULL,
  `rejection_reason` varchar(500) DEFAULT NULL,
  `responded_at` datetime DEFAULT NULL,
  `created_by` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ec_event_entity` (`event_id`,`entity_id`,`entity_type`),
  KEY `fk_ec_created` (`created_by`),
  KEY `fk_ec_updated` (`updated_by`),
  KEY `idx_ec_event` (`event_id`),
  KEY `idx_ec_entity` (`entity_id`,`entity_type`),
  KEY `idx_ec_invite_status` (`event_id`,`invite_status`),
  CONSTRAINT `fk_ec_created` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_ec_event` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ec_updated` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `events_interest` (
  `id` varchar(36) NOT NULL,
  `event_id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `expressed_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ei_event_user` (`event_id`,`user_id`),
  KEY `idx_ei_event` (`event_id`),
  KEY `idx_ei_user` (`user_id`),
  CONSTRAINT `fk_ei_event` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ei_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `events_log` (
  `id` varchar(36) NOT NULL,
  `event_id` varchar(36) NOT NULL,
  `edited_by` varchar(36) NOT NULL,
  `changed_fields` json NOT NULL,
  `edited_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_el_editor` (`edited_by`),
  KEY `idx_el_event_time` (`event_id`,`edited_at`),
  CONSTRAINT `fk_el_editor` FOREIGN KEY (`edited_by`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_el_event` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `ig_opportunity` (
  `id` varchar(36) NOT NULL,
  `ig_id` varchar(36) DEFAULT NULL,
  `type` enum('CHALLENGE','INTERNSHIP','HACKATHON','JOB') NOT NULL,
  `title` varchar(150) NOT NULL,
  `description` text NOT NULL,
  `eligibility` text,
  `application_url` varchar(500) DEFAULT NULL,
  `starts_at` datetime DEFAULT NULL,
  `ends_at` datetime DEFAULT NULL,
  `status` enum('DRAFT','PUBLISHED','CLOSED','ARCHIVED') NOT NULL DEFAULT 'DRAFT',
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `org_id` varchar(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_opp_ig_type_status` (`ig_id`,`type`,`status`),
  KEY `fk_io_org` (`org_id`),
  CONSTRAINT `fk_io_org` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_opp_ig` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `intern_daily_timesheet` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `entry_date` date NOT NULL,
  `category` varchar(50) NOT NULL,
  `description` text NOT NULL,
  `hours` decimal(4,2) NOT NULL,
  `task` json DEFAULT NULL,
  `blockers` text,
  `end_of_day_note` text,
  `edit_reason` varchar(300) DEFAULT NULL,
  `status` varchar(15) NOT NULL DEFAULT 'PENDING',
  `reviewed_by` varchar(36) DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `review_note` varchar(300) DEFAULT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_timesheet_user_date` (`user_id`,`entry_date`),
  KEY `fk_ts_created_by` (`created_by`),
  KEY `fk_ts_updated_by` (`updated_by`),
  KEY `fk_ts_reviewed_by` (`reviewed_by`),
  CONSTRAINT `fk_ts_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ts_reviewed_by` FOREIGN KEY (`reviewed_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_ts_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ts_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `intern_guild_minute` (
  `id` varchar(36) NOT NULL,
  `guild` varchar(75) NOT NULL,
  `date` date NOT NULL,
  `title` varchar(200) NOT NULL,
  `minutes` longtext NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_igm_created_by` (`created_by`),
  KEY `fk_igm_updated_by` (`updated_by`),
  KEY `idx_igm_guild_date` (`guild`,`date`),
  CONSTRAINT `fk_igm_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_igm_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `intern_leave_request` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `leave_type` varchar(20) NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `duration_days` smallint NOT NULL,
  `reason` text NOT NULL,
  `status` varchar(15) NOT NULL DEFAULT 'PENDING',
  `reviewed_by` varchar(36) DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `review_note` varchar(300) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_leave_user_status` (`user_id`,`status`),
  KEY `idx_leave_dates` (`start_date`,`end_date`),
  KEY `fk_leave_reviewed_by` (`reviewed_by`),
  CONSTRAINT `fk_leave_reviewed_by` FOREIGN KEY (`reviewed_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_leave_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- intern_task includes `remark` (added by a later ALTER in alter-1.80.sql; baked in here)
CREATE TABLE `intern_task` (
  `id` varchar(36) NOT NULL,
  `title` varchar(150) NOT NULL,
  `description` text NOT NULL,
  `assigned_to` varchar(36) NOT NULL,
  `team` varchar(75) NOT NULL,
  `category` varchar(50) NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'NOT_STARTED',
  `complexity` varchar(10) NOT NULL DEFAULT 'LOW',
  `deadline` date NOT NULL,
  `iso_week` tinyint NOT NULL,
  `is_archived` tinyint NOT NULL DEFAULT '0',
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `karma_awarded` int DEFAULT '0',
  `output_link` varchar(500) DEFAULT NULL,
  `is_verified` tinyint(1) DEFAULT '0',
  `verified_by_id` varchar(36) DEFAULT NULL,
  `remark` longtext DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_task_assigned` (`assigned_to`,`status`),
  KEY `idx_task_team_week` (`team`,`iso_week`),
  KEY `fk_task_created_by` (`created_by`),
  KEY `fk_task_updated_by` (`updated_by`),
  KEY `fk_task_verified_by` (`verified_by_id`),
  CONSTRAINT `fk_task_assigned` FOREIGN KEY (`assigned_to`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_verified_by` FOREIGN KEY (`verified_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `intern_weekly_review` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `iso_year` smallint NOT NULL,
  `iso_week` tinyint NOT NULL,
  `week_start_date` date NOT NULL,
  `week_end_date` date NOT NULL,
  `team` varchar(75) NOT NULL,
  `is_on_leave` tinyint NOT NULL DEFAULT '0',
  `tasks_completed` json DEFAULT NULL,
  `weekly_review` text NOT NULL,
  `task_remarks` json DEFAULT NULL,
  `hours_committed` decimal(5,2) NOT NULL,
  `blockers` text,
  `leave_days` text,
  `suggestions` text,
  `is_late` tinyint NOT NULL DEFAULT '0',
  `status` varchar(15) NOT NULL DEFAULT 'PENDING',
  `reviewed_by` varchar(36) DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `review_note` varchar(300) DEFAULT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `tasks_assigned` json DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_review_user_week` (`user_id`,`iso_year`,`iso_week`),
  KEY `fk_wr_created_by` (`created_by`),
  KEY `fk_wr_updated_by` (`updated_by`),
  KEY `fk_wr_reviewed_by` (`reviewed_by`),
  CONSTRAINT `fk_wr_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_wr_reviewed_by` FOREIGN KEY (`reviewed_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_wr_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_wr_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `mentor_availability_slot` (
  `id` varchar(36) NOT NULL,
  `mentor_user_id` varchar(36) NOT NULL,
  `ig_id` varchar(36) DEFAULT NULL,
  `weekday` tinyint NOT NULL COMMENT '1=Mon ... 7=Sun',
  `start_time` time NOT NULL,
  `end_time` time NOT NULL,
  `timezone` varchar(64) NOT NULL DEFAULT 'Asia/Kolkata',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `valid_from` date DEFAULT NULL,
  `valid_to` date DEFAULT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_avail_ig` (`ig_id`),
  KEY `idx_mas_active_mentor` (`mentor_user_id`,`is_active`),
  KEY `fk_avail_created_by` (`created_by`),
  KEY `fk_avail_updated_by` (`updated_by`),
  CONSTRAINT `fk_avail_ig` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_avail_mentor` FOREIGN KEY (`mentor_user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_avail_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_avail_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_avail_time` CHECK ((`start_time` < `end_time`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- mentorship_session includes requested_by + REQUESTED status (added by a later
-- migration block in alter-1.80.sql; baked in here as the final state)
CREATE TABLE `mentorship_session` (
  `id` varchar(36) NOT NULL,
  `entity_id` varchar(36) DEFAULT NULL,
  `title` varchar(150) NOT NULL,
  `description` text,
  `mode` enum('ONLINE','OFFLINE','HYBRID') NOT NULL DEFAULT 'ONLINE',
  `starts_at` datetime NOT NULL,
  `ends_at` datetime NOT NULL,
  `meeting_link` varchar(500) DEFAULT NULL,
  `venue` varchar(255) DEFAULT NULL,
  `status` enum('REQUESTED','PENDING_APPROVAL','SCHEDULED','COMPLETED','CANCELLED','REJECTED') NOT NULL COMMENT 'REQUESTED = student-initiated, awaiting mentor review',
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `approved_by` varchar(36) DEFAULT NULL,
  `approved_at` datetime DEFAULT NULL,
  `requested_by` varchar(36) DEFAULT NULL COMMENT 'ID of the student who originally requested this session. NULL for mentor-created sessions.',
  `max_participants` int DEFAULT NULL,
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0',
  `session_type` varchar(20) NOT NULL DEFAULT 'ig_session',
  `is_recurring` tinyint(1) DEFAULT '0',
  `recurrence_type` varchar(20) DEFAULT NULL,
  `recurrence_interval` int DEFAULT NULL,
  `recurrence_end_date` date DEFAULT NULL,
  `parent_session_id` varchar(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_session_ig` (`entity_id`),
  KEY `fk_mentorship_session_approved_by` (`approved_by`),
  KEY `fk_mentorship_session_parent` (`parent_session_id`),
  KEY `fk_mentorship_session_created_by` (`created_by`),
  KEY `fk_mentorship_session_updated_by` (`updated_by`),
  CONSTRAINT `fk_mentorship_session_approved_by` FOREIGN KEY (`approved_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_mentorship_session_parent` FOREIGN KEY (`parent_session_id`) REFERENCES `mentorship_session` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_mentorship_session_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mentorship_session_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mentorship_session_requested_by` FOREIGN KEY (`requested_by`) REFERENCES `user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `chk_session_time` CHECK ((`starts_at` < `ends_at`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `mentor_karma_award` (
  `id` varchar(36) NOT NULL,
  `session_id` varchar(36) NOT NULL,
  `mentor_id` varchar(36) NOT NULL,
  `karma` int NOT NULL,
  `note` varchar(500) DEFAULT NULL,
  `awarded_by` varchar(36) NOT NULL,
  `awarded_at` datetime NOT NULL,
  `kal_id` varchar(36) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_mka_session_mentor` (`session_id`,`mentor_id`),
  KEY `fk_mka_mentor` (`mentor_id`),
  KEY `fk_mka_awarded` (`awarded_by`),
  KEY `fk_mka_kal` (`kal_id`),
  CONSTRAINT `fk_mka_awarded` FOREIGN KEY (`awarded_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mka_kal` FOREIGN KEY (`kal_id`) REFERENCES `karma_activity_log` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_mka_mentor` FOREIGN KEY (`mentor_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mka_session` FOREIGN KEY (`session_id`) REFERENCES `mentorship_session` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `mentor_session` (
  `id` varchar(36) NOT NULL,
  `mentor_id` varchar(36) NOT NULL,
  `mentee_id` varchar(36) NOT NULL,
  `ig_id` varchar(36) DEFAULT NULL,
  `title` varchar(200) NOT NULL,
  `description` text,
  `scheduled_at` datetime NOT NULL,
  `duration_minutes` int NOT NULL,
  `status` enum('scheduled','completed','cancelled') NOT NULL DEFAULT 'scheduled',
  `meeting_link` varchar(500) DEFAULT NULL,
  `notes` text,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `mentor_id` (`mentor_id`),
  KEY `mentee_id` (`mentee_id`),
  KEY `ig_id` (`ig_id`),
  KEY `created_by` (`created_by`),
  KEY `updated_by` (`updated_by`),
  CONSTRAINT `mentor_session_ibfk_1` FOREIGN KEY (`mentor_id`) REFERENCES `user` (`id`),
  CONSTRAINT `mentor_session_ibfk_2` FOREIGN KEY (`mentee_id`) REFERENCES `user` (`id`),
  CONSTRAINT `mentor_session_ibfk_3` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`),
  CONSTRAINT `mentor_session_ibfk_4` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`),
  CONSTRAINT `mentor_session_ibfk_5` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `mentor_task_request` (
  `id` varchar(36) NOT NULL DEFAULT (uuid()),
  `mentor_id` varchar(36) NOT NULL,
  `ig_id` varchar(36) NOT NULL,
  `title` varchar(75) NOT NULL,
  `hashtag` varchar(75) NOT NULL,
  `karma` int NOT NULL,
  `description` text,
  `status` enum('PENDING','APPROVED','REJECTED') NOT NULL DEFAULT 'PENDING',
  `admin_note` varchar(500) DEFAULT NULL,
  `reviewed_by` varchar(36) DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `created_task_id` varchar(36) DEFAULT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_mtr_reviewed_by` (`reviewed_by`),
  KEY `fk_mtr_created_task` (`created_task_id`),
  KEY `fk_mtr_created_by` (`created_by`),
  KEY `fk_mtr_updated_by` (`updated_by`),
  KEY `idx_mtr_mentor` (`mentor_id`),
  KEY `idx_mtr_ig` (`ig_id`),
  KEY `idx_mtr_status` (`status`),
  CONSTRAINT `fk_mtr_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_mtr_created_task` FOREIGN KEY (`created_task_id`) REFERENCES `task_list` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_mtr_ig` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mtr_mentor` FOREIGN KEY (`mentor_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mtr_reviewed_by` FOREIGN KEY (`reviewed_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_mtr_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `mentorship_session_user_link` (
  `id` varchar(36) NOT NULL,
  `session_id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `participant_role` enum('MENTOR','MENTEE','CO_MENTOR') NOT NULL,
  `attendance_status` enum('INVITED','ATTENDED','ABSENT') NOT NULL DEFAULT 'INVITED',
  `progress_note` varchar(500) DEFAULT NULL,
  `contributed_minutes` int DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `feedback` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_session_user_role` (`session_id`,`user_id`,`participant_role`),
  KEY `idx_session_role` (`session_id`,`participant_role`),
  KEY `idx_user_role` (`user_id`,`participant_role`),
  CONSTRAINT `fk_sul_session` FOREIGN KEY (`session_id`) REFERENCES `mentorship_session` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sul_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_contrib_minutes` CHECK (((`contributed_minutes` is null) or (`contributed_minutes` > 0)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `projects` (
  `id` varchar(36) NOT NULL,
  `logo` varchar(255) DEFAULT NULL,
  `title` varchar(50) NOT NULL,
  `description` text NOT NULL,
  `status` enum('draft','published','archived') NOT NULL DEFAULT 'published',
  `created_by` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_projects_created_by` (`created_by`),
  KEY `idx_projects_status` (`status`),
  KEY `fk_projects_updated_by` (`updated_by`),
  CONSTRAINT `fk_projects_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_projects_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `project_images` (
  `id` varchar(36) NOT NULL,
  `project_id` varchar(36) NOT NULL,
  `image` varchar(255) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_project_images_project` (`project_id`),
  CONSTRAINT `fk_project_images_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `project_links` (
  `id` varchar(36) NOT NULL,
  `project_id` varchar(36) NOT NULL,
  `label` varchar(50) NOT NULL,
  `url` varchar(500) NOT NULL,
  `position` int NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_project_links_project` (`project_id`),
  CONSTRAINT `fk_project_links_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `project_members` (
  `id` varchar(36) NOT NULL,
  `project_id` varchar(36) NOT NULL,
  `user_id` varchar(36) DEFAULT NULL,
  `external_name` varchar(100) DEFAULT NULL,
  `role` varchar(50) DEFAULT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_project_member_user` (`project_id`,`user_id`),
  KEY `idx_project_members_project` (`project_id`),
  KEY `fk_pm_user` (`user_id`),
  KEY `fk_pm_created_by` (`created_by`),
  CONSTRAINT `fk_pm_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_pm_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_pm_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_member_identity` CHECK ((((`user_id` is not null) and (`external_name` is null)) or ((`user_id` is null) and (`external_name` is not null))))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `project_skill_link` (
  `id` varchar(36) NOT NULL,
  `project_id` varchar(36) NOT NULL,
  `skill_id` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_project_skill` (`project_id`,`skill_id`),
  KEY `fk_psl_skill` (`skill_id`),
  CONSTRAINT `fk_psl_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_psl_skill` FOREIGN KEY (`skill_id`) REFERENCES `skill` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `projects_comments` (
  `id` varchar(36) NOT NULL,
  `comment` text NOT NULL,
  `project_id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_pc_project` (`project_id`),
  KEY `fk_pc_user` (`user_id`),
  KEY `fk_pc_created_by` (`created_by`),
  KEY `fk_pc_updated_by` (`updated_by`),
  CONSTRAINT `fk_pc_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_pc_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_pc_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_pc_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `projects_votes` (
  `id` varchar(36) NOT NULL,
  `vote` varchar(10) NOT NULL,
  `project_id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_projects_votes_user_project` (`user_id`,`project_id`),
  KEY `fk_pv_project` (`project_id`),
  KEY `fk_pv_created_by` (`created_by`),
  KEY `fk_pv_updated_by` (`updated_by`),
  CONSTRAINT `fk_pv_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_pv_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_pv_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_pv_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `system_action_log` (
  `id` varchar(36) NOT NULL,
  `action_type` enum('PERSONA_SWITCH','TASK_REVIEW','EVENT_REVIEW','SESSION_CREATE','SESSION_UPDATE','SESSION_STATUS','KARMA_AWARD','MANUAL_HOURS_LOG','IG_CONTENT_UPDATE','OPPORTUNITY_POST','MENTOR_VERIFY','INTERN_TASK_UPDATE','INTERN_LEAVE_REQUEST','INTERN_LEAVE_REVIEW','INTERN_TIMESHEET_EDIT','INTERN_GUILD_REASSIGN') NOT NULL,
  `actor_user_id` varchar(36) NOT NULL,
  `subject_user_id` varchar(36) DEFAULT NULL,
  `ig_id` varchar(36) DEFAULT NULL,
  `entity_name` varchar(50) NOT NULL,
  `entity_id` varchar(36) NOT NULL,
  `old_data` json DEFAULT NULL,
  `new_data` json DEFAULT NULL,
  `remarks` varchar(500) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_log_actor_time` (`actor_user_id`,`created_at`),
  KEY `idx_log_ig_time` (`ig_id`,`created_at`),
  KEY `idx_log_entity` (`entity_name`,`entity_id`),
  KEY `fk_log_subject` (`subject_user_id`),
  CONSTRAINT `fk_log_actor` FOREIGN KEY (`actor_user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_log_ig` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_log_subject` FOREIGN KEY (`subject_user_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `user_ig_lvl_link` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `ig_id` varchar(36) NOT NULL,
  `level_id` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user_ig` (`user_id`,`ig_id`),
  KEY `ig_id` (`ig_id`),
  KEY `level_id` (`level_id`),
  KEY `created_by` (`created_by`),
  KEY `updated_by` (`updated_by`),
  CONSTRAINT `user_ig_lvl_link_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_ig_lvl_link_ibfk_2` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_ig_lvl_link_ibfk_3` FOREIGN KEY (`level_id`) REFERENCES `level` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_ig_lvl_link_ibfk_4` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_ig_lvl_link_ibfk_5` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `user_ig_lvl_log` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `ig_id` varchar(36) NOT NULL,
  `level_id` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `ig_id` (`ig_id`),
  KEY `level_id` (`level_id`),
  CONSTRAINT `user_ig_lvl_log_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_ig_lvl_log_ibfk_2` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_ig_lvl_log_ibfk_3` FOREIGN KEY (`level_id`) REFERENCES `level` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `user_intern_guild_link` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `guild` varchar(75) NOT NULL,
  `status` varchar(15) NOT NULL DEFAULT 'ACTIVE',
  `previous_status` varchar(15) DEFAULT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_intern_guild_user` (`user_id`),
  KEY `idx_intern_guild_status` (`status`),
  KEY `idx_intern_guild_name` (`guild`),
  KEY `fk_intern_guild_created_by` (`created_by`),
  KEY `fk_intern_guild_updated_by` (`updated_by`),
  CONSTRAINT `fk_intern_guild_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_intern_guild_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_intern_guild_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `user_job_application` (
  `id` varchar(36) NOT NULL,
  `job_id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `resume_link` text,
  `cover_letter` text,
  `status` enum('Pending','In-Review','Shortlisted','Interview','Rejected','Selected') NOT NULL DEFAULT 'Pending',
  `rejection_reason` text,
  `applied_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_job_user` (`job_id`,`user_id`),
  KEY `fk_application_user` (`user_id`),
  CONSTRAINT `fk_application_job` FOREIGN KEY (`job_id`) REFERENCES `company_jobs` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_application_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `user_partner` (
  `id` varchar(36) NOT NULL DEFAULT (uuid()),
  `user_link_id` varchar(36) NOT NULL,
  `name` varchar(255) NOT NULL,
  `slug` varchar(255) NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'pending',
  `rejection_reason` text,
  `description` text,
  `email` varchar(100) NOT NULL,
  `logo` text,
  `short_pitch` varchar(900) DEFAULT NULL,
  `location` varchar(150) DEFAULT NULL,
  `district_id` varchar(36) DEFAULT NULL,
  `state_id` varchar(36) DEFAULT NULL,
  `country_id` varchar(36) DEFAULT NULL,
  `partner_type` varchar(75) DEFAULT NULL,
  `website_link` text,
  `social_links` json DEFAULT NULL,
  `submitted_at` datetime DEFAULT NULL,
  `verified_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_by` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) DEFAULT NULL,
  `verified_by` varchar(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_partner_user_link` (`user_link_id`),
  UNIQUE KEY `uk_user_partner_name` (`name`),
  UNIQUE KEY `uk_user_partner_slug` (`slug`),
  KEY `fk_user_partner_district` (`district_id`),
  KEY `fk_user_partner_state` (`state_id`),
  KEY `fk_user_partner_country` (`country_id`),
  KEY `fk_user_partner_created_by` (`created_by`),
  KEY `fk_user_partner_updated_by` (`updated_by`),
  KEY `fk_user_partner_verified_by` (`verified_by`),
  CONSTRAINT `fk_user_partner_country` FOREIGN KEY (`country_id`) REFERENCES `country` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_user_partner_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_user_partner_district` FOREIGN KEY (`district_id`) REFERENCES `district` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_user_partner_state` FOREIGN KEY (`state_id`) REFERENCES `state` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_user_partner_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_user_partner_user_link` FOREIGN KEY (`user_link_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_partner_verified_by` FOREIGN KEY (`verified_by`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `user_role_link_backup` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `role_id` varchar(36) NOT NULL,
  `ig_id` varchar(36) DEFAULT NULL,
  `verified` tinyint(1) NOT NULL DEFAULT '0',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `is_primary` tinyint(1) NOT NULL DEFAULT '0',
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `revoked_at` datetime DEFAULT NULL,
  `revoked_by` varchar(36) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `mentor_scope_grant` (
  `id` varchar(36) NOT NULL,
  `mentor_id` varchar(36) NOT NULL,
  `scope_type` varchar(14) NOT NULL,
  `scope_id` varchar(36) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `granted_by` varchar(36) NOT NULL,
  `granted_at` datetime NOT NULL,
  `revoked_by` varchar(36) DEFAULT NULL,
  `revoked_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_mentor_scope_grant` (`mentor_id`,`scope_type`,`scope_id`),
  KEY `idx_mentor_scope_grant_scope` (`scope_type`,`scope_id`,`is_active`),
  CONSTRAINT `fk_msg_mentor` FOREIGN KEY (`mentor_id`) REFERENCES `user_mentor` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_msg_granted_by` FOREIGN KEY (`granted_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_msg_revoked_by` FOREIGN KEY (`revoked_by`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================================
-- alter-1.80.sql sync: column/index/FK additions to existing tables
-- (circle_meeting_log.is_recurring/recurrence_type/recurrence already exist
-- in this file from an earlier migration -- alter-1.80.sql re-adds them
-- guarded/idempotently in production, so no action needed here.)
-- ============================================================================

ALTER TABLE college
    ADD COLUMN lead_id VARCHAR(36) DEFAULT NULL,
    ADD KEY fk_college_ref_lead (lead_id),
    ADD CONSTRAINT fk_college_ref_lead FOREIGN KEY (lead_id) REFERENCES user (id) ON DELETE CASCADE;

ALTER TABLE interest_group
    ADD COLUMN status ENUM('active','requested','cancelled','rejected') NOT NULL DEFAULT 'requested';

ALTER TABLE karma_activity_log
    ADD COLUMN mentor_review_status ENUM('PENDING','APPROVED','REJECTED') NOT NULL DEFAULT 'PENDING',
    ADD COLUMN mentor_reviewed_by VARCHAR(36) DEFAULT NULL,
    ADD COLUMN mentor_reviewed_at DATETIME DEFAULT NULL,
    ADD COLUMN mentor_review_feedback VARCHAR(500) DEFAULT NULL,
    ADD COLUMN proof_link VARCHAR(500) DEFAULT NULL COMMENT 'Proof URL submitted by mentee for task verification',
    ADD COLUMN remarks TEXT COMMENT 'Mentor remarks on approval or rejection',
    ADD KEY fk_karma_activity_log_ref_mentor_reviewed_by (mentor_reviewed_by),
    ADD CONSTRAINT fk_karma_activity_log_ref_mentor_reviewed_by FOREIGN KEY (mentor_reviewed_by) REFERENCES user (id) ON DELETE SET NULL;

ALTER TABLE level
    ADD COLUMN level_system_id VARCHAR(36) NOT NULL DEFAULT (UUID()),
    ADD KEY fk_level_ref_level_system (level_system_id),
    ADD CONSTRAINT fk_level_ref_level_system FOREIGN KEY (level_system_id) REFERENCES level_system (id) ON DELETE CASCADE;

ALTER TABLE task_list
    ADD COLUMN event_id VARCHAR(36) DEFAULT NULL,
    ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'draft',
    ADD COLUMN requested_by VARCHAR(36) DEFAULT NULL,
    ADD COLUMN requested_at DATETIME DEFAULT NULL,
    ADD COLUMN approved_by VARCHAR(36) DEFAULT NULL,
    ADD COLUMN approved_at DATETIME DEFAULT NULL,
    ADD COLUMN reason VARCHAR(500) DEFAULT NULL,
    ADD COLUMN approval_status VARCHAR(20) NOT NULL DEFAULT 'approved' COMMENT 'approved | pending | rejected',
    ADD COLUMN submitted_by_company_id VARCHAR(36) DEFAULT NULL COMMENT 'FK to company.id, NULL for admin-created tasks',
    ADD COLUMN rejection_reason TEXT,
    ADD COLUMN reviewed_by_admin_id VARCHAR(36) DEFAULT NULL,
    ADD COLUMN reviewed_at DATETIME DEFAULT NULL,
    ADD KEY fk_task_list_ref_event_id (event_id),
    ADD CONSTRAINT fk_task_list_ref_event_id FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE SET NULL,
    ADD KEY fk_task_list_ref_requested_by (requested_by),
    ADD CONSTRAINT fk_task_list_ref_requested_by FOREIGN KEY (requested_by) REFERENCES user (id) ON DELETE SET NULL,
    ADD KEY fk_task_list_ref_reviewed_by_admin (reviewed_by_admin_id),
    ADD CONSTRAINT fk_task_list_ref_reviewed_by_admin FOREIGN KEY (reviewed_by_admin_id) REFERENCES user (id) ON DELETE SET NULL,
    ADD KEY fk_task_list_ref_company (submitted_by_company_id),
    ADD CONSTRAINT fk_task_list_ref_company FOREIGN KEY (submitted_by_company_id) REFERENCES company (id) ON DELETE SET NULL;

ALTER TABLE task_type
    ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT '1';

ALTER TABLE user_circle_link
    ADD COLUMN invited_by VARCHAR(36) DEFAULT NULL,
    ADD COLUMN assignment_type ENUM('MENTOR','LEARNER','LEAD','MODERATOR') NOT NULL DEFAULT 'LEARNER',
    ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT '1',
    ADD COLUMN assigned_by VARCHAR(36) DEFAULT NULL,
    ADD COLUMN unassigned_at DATETIME DEFAULT NULL;

ALTER TABLE user_ig_link
    ADD COLUMN assignment_type ENUM('MENTOR','LEARNER','LEAD','MODERATOR') NOT NULL DEFAULT 'LEARNER',
    ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT '1',
    ADD COLUMN assigned_by VARCHAR(36) DEFAULT NULL,
    ADD COLUMN unassigned_at DATETIME DEFAULT NULL,
    ADD KEY fk_uil_assigned_by (assigned_by),
    ADD CONSTRAINT fk_uil_assigned_by FOREIGN KEY (assigned_by) REFERENCES user (id) ON DELETE SET NULL;

ALTER TABLE user_mentor
    ADD COLUMN expertise TEXT,
    ADD COLUMN mentor_tier ENUM('IG_MENTOR','MENTOR','COMPANY_MENTOR','CAMPUS_MENTOR') NOT NULL DEFAULT 'MENTOR',
    ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    ADD COLUMN verified_by VARCHAR(36) DEFAULT NULL,
    ADD COLUMN verified_at DATETIME DEFAULT NULL,
    ADD COLUMN verification_note VARCHAR(500) DEFAULT NULL,
    ADD COLUMN preferred_ig_ids JSON DEFAULT NULL COMMENT 'JSON list of IG UUIDs the mentor prefers; auto-creates UserIgLink on verification',
    ADD COLUMN org_id VARCHAR(36) DEFAULT NULL,
    ADD KEY fk_user_mentor_ref_verified_by (verified_by),
    ADD CONSTRAINT fk_user_mentor_ref_verified_by FOREIGN KEY (verified_by) REFERENCES user (id) ON DELETE SET NULL,
    ADD KEY fk_user_mentor_ref_org_id (org_id),
    ADD CONSTRAINT fk_user_mentor_ref_org_id FOREIGN KEY (org_id) REFERENCES organization (id) ON DELETE SET NULL;

ALTER TABLE user_role_link
    ADD COLUMN ig_id VARCHAR(36) DEFAULT NULL,
    ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT '1',
    ADD COLUMN is_primary TINYINT(1) NOT NULL DEFAULT '0',
    ADD COLUMN revoked_at DATETIME DEFAULT NULL,
    ADD COLUMN revoked_by VARCHAR(36) DEFAULT NULL,
    ADD KEY fk_user_role_link_ref_ig_id (ig_id),
    ADD CONSTRAINT fk_user_role_link_ref_ig_id FOREIGN KEY (ig_id) REFERENCES interest_group (id) ON DELETE CASCADE,
    ADD KEY fk_user_role_link_ref_revoked_by (revoked_by),
    ADD CONSTRAINT fk_user_role_link_ref_revoked_by FOREIGN KEY (revoked_by) REFERENCES user (id) ON DELETE SET NULL;

ALTER TABLE user_settings
    ADD COLUMN active_persona ENUM('learner','mentor') NOT NULL DEFAULT 'learner',
    ADD COLUMN active_role_link_id VARCHAR(36) DEFAULT NULL,
    ADD COLUMN active_ig_id VARCHAR(36) DEFAULT NULL,
    ADD COLUMN last_persona_switched_at DATETIME DEFAULT NULL,
    ADD KEY fk_user_settings_ref_active_role_link (active_role_link_id),
    ADD CONSTRAINT fk_user_settings_ref_active_role_link FOREIGN KEY (active_role_link_id) REFERENCES user_role_link (id) ON DELETE SET NULL,
    ADD KEY fk_user_settings_ref_active_ig (active_ig_id),
    ADD CONSTRAINT fk_user_settings_ref_active_ig FOREIGN KEY (active_ig_id) REFERENCES interest_group (id) ON DELETE SET NULL;

-- events.category_id FK, added now that `categories` exists (see events CREATE TABLE above)
ALTER TABLE events
    ADD CONSTRAINT fk_events_category FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL;

ALTER TABLE `user` MODIFY COLUMN `gender` VARCHAR(20);

CREATE TABLE `impact_project` (
  `id` varchar(36) NOT NULL,
  `ig_id` varchar(36) NOT NULL,
  `title` varchar(200) NOT NULL,
  `description` text NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_impact_project_ref_ig` (`ig_id`),
  KEY `fk_impact_project_ref_updated_by` (`updated_by`),
  KEY `fk_impact_project_ref_created_by` (`created_by`),
  CONSTRAINT `fk_impact_project_ref_ig` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_impact_project_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_impact_project_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `impact_project_user_link` (
  `id` varchar(36) NOT NULL,
  `project_id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `is_lead` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_impact_project_user_link` (`project_id`, `user_id`),
  KEY `fk_impact_project_user_link_ref_user` (`user_id`),
  CONSTRAINT `fk_impact_project_user_link_ref_project` FOREIGN KEY (`project_id`) REFERENCES `impact_project` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_impact_project_user_link_ref_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `impact_project_link` (
  `id` varchar(36) NOT NULL,
  `project_id` varchar(36) NOT NULL,
  `label` varchar(50) NOT NULL,
  `url` varchar(500) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_ipl_project` (`project_id`),
  CONSTRAINT `fk_impact_project_link_ref_project` FOREIGN KEY (`project_id`) REFERENCES `impact_project` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `comic` (
  `id` varchar(36) NOT NULL,
  `title` varchar(150) NOT NULL,
  `slug` varchar(180) NOT NULL,
  `description` text,
  `cover_image_key` varchar(255) DEFAULT NULL,
  `status` enum('draft','published','archived') NOT NULL DEFAULT 'draft',
  `like_count` int NOT NULL DEFAULT '0',
  `comment_count` int NOT NULL DEFAULT '0',
  `bookmark_count` int NOT NULL DEFAULT '0',
  `published_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted_by` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  KEY `fk_comic_deleted_by` (`deleted_by`),
  KEY `fk_comic_updated_by` (`updated_by`),
  KEY `idx_comic_status_created` (`status`,`created_at`),
  KEY `idx_comic_created_by` (`created_by`),
  CONSTRAINT `fk_comic_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_deleted_by` FOREIGN KEY (`deleted_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_comic_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `comic_bookmark_link` (
  `id` varchar(36) NOT NULL,
  `comic_id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_comic_bookmark` (`comic_id`,`user_id`),
  KEY `fk_comic_bookmark_link_ref_created_by` (`created_by`),
  KEY `idx_comic_bookmark_user` (`user_id`),
  CONSTRAINT `fk_comic_bookmark_link_ref_comic_id` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_bookmark_link_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_bookmark_link_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `genre` (
  `id` varchar(36) NOT NULL,
  `name` varchar(75) NOT NULL,
  `slug` varchar(90) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `slug` (`slug`),
  KEY `fk_genre_updated_by` (`updated_by`),
  KEY `fk_genre_created_by` (`created_by`),
  CONSTRAINT `fk_genre_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_genre_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `comic_genre_link` (
  `id` varchar(36) NOT NULL,
  `comic_id` varchar(36) NOT NULL,
  `genre_id` varchar(36) NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_comic_genre` (`comic_id`,`genre_id`),
  KEY `fk_comic_genre_created_by` (`created_by`),
  KEY `idx_comic_genre_genre` (`genre_id`),
  CONSTRAINT `fk_comic_genre_comic` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_genre_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_genre_genre` FOREIGN KEY (`genre_id`) REFERENCES `genre` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `comic_contributor_link` (
  `id` varchar(36) NOT NULL,
  `comic_id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `contributor_type` enum('creator','writer','artist','colorist','editor') NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_comic_contributor` (`comic_id`,`user_id`,`contributor_type`),
  KEY `fk_contributor_created_by` (`created_by`),
  KEY `idx_contributor_user` (`user_id`),
  KEY `idx_contributor_comic_type` (`comic_id`,`contributor_type`),
  CONSTRAINT `fk_contributor_comic` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_contributor_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_contributor_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `chapter` (
  `id` varchar(36) NOT NULL,
  `comic_id` varchar(36) NOT NULL,
  `title` varchar(150) NOT NULL,
  `slug` varchar(75) NOT NULL,
  `description` text,
  `chapter_number` decimal(6,2) NOT NULL,
  `cover_image_key` varchar(255) DEFAULT NULL,
  `status` varchar(10) NOT NULL DEFAULT 'draft',
  `published_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted_by` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  UNIQUE KEY `uq_comic_chapter_number` (`comic_id`,`chapter_number`),
  KEY `idx_chapter_status_created` (`status`,`created_at`),
  KEY `idx_chapter_comic_status` (`comic_id`,`status`),
  KEY `fk_chapter_ref_del_by` (`deleted_by`),
  KEY `fk_chapter_ref_upd_by` (`updated_by`),
  KEY `fk_chapter_ref_cre_by` (`created_by`),
  CONSTRAINT `fk_chapter_ref_comic_id` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chapter_ref_cre_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chapter_ref_del_by` FOREIGN KEY (`deleted_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_chapter_ref_upd_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `chapter_page` (
  `id` varchar(36) NOT NULL,
  `chapter_id` varchar(36) NOT NULL,
  `page_number` int unsigned NOT NULL,
  `image_key` varchar(255) NOT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted_by` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_chapter_page_number` (`chapter_id`,`page_number`),
  KEY `idx_chapter_page_order` (`chapter_id`,`page_number`),
  KEY `fk_chapter_page_ref_del_by` (`deleted_by`),
  KEY `fk_chapter_page_ref_upd_by` (`updated_by`),
  KEY `fk_chapter_page_ref_cre_by` (`created_by`),
  CONSTRAINT `fk_chapter_page_ref_chapter_id` FOREIGN KEY (`chapter_id`) REFERENCES `chapter` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chapter_page_ref_cre_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chapter_page_ref_del_by` FOREIGN KEY (`deleted_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_chapter_page_ref_upd_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `comic_like_link` (
  `id` varchar(36) NOT NULL,
  `comic_id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_comic_like` (`comic_id`,`user_id`),
  KEY `fk_comic_like_link_ref_created_by` (`created_by`),
  KEY `idx_comic_like_user` (`user_id`),
  CONSTRAINT `fk_comic_like_link_ref_comic_id` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_like_link_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_like_link_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `comic_reading_progress` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `comic_id` varchar(36) NOT NULL,
  `last_chapter_id` varchar(36) DEFAULT NULL,
  `last_page_number` int DEFAULT NULL,
  `updated_at` datetime NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_reading_progress` (`user_id`,`comic_id`),
  KEY `fk_comic_reading_progress_ref_comic_id` (`comic_id`),
  KEY `fk_comic_reading_progress_ref_last_chapter_id` (`last_chapter_id`),
  CONSTRAINT `fk_comic_reading_progress_ref_comic_id` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_reading_progress_ref_last_chapter_id` FOREIGN KEY (`last_chapter_id`) REFERENCES `chapter` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_comic_reading_progress_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `comic_comment` (
  `id` varchar(36) NOT NULL,
  `comic_id` varchar(36) NOT NULL,
  `chapter_id` varchar(36) DEFAULT NULL,
  `parent_id` varchar(36) DEFAULT NULL,
  `user_id` varchar(36) NOT NULL,
  `message` text NOT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted_by` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_comic_comment_ref_chapter_id` (`chapter_id`),
  KEY `fk_comic_comment_ref_parent_id` (`parent_id`),
  KEY `fk_comic_comment_ref_user_id` (`user_id`),
  KEY `fk_comic_comment_ref_updated_by` (`updated_by`),
  KEY `fk_comic_comment_ref_created_by` (`created_by`),
  KEY `idx_comic_comment_comic` (`comic_id`,`created_at`),
  CONSTRAINT `fk_comic_comment_ref_chapter_id` FOREIGN KEY (`chapter_id`) REFERENCES `chapter` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_comment_ref_comic_id` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_comment_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_comment_ref_parent_id` FOREIGN KEY (`parent_id`) REFERENCES `comic_comment` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_comment_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_comment_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO system_setting (`key`, value, updated_at, created_at)
    VALUES ('db.version', '1.84', now(), now());

ALTER TABLE user_lvl_link 
ADD COLUMN grit INT NOT NULL DEFAULT 50 AFTER level_id,
ADD COLUMN last_level_down_at DATETIME DEFAULT NULL AFTER grit;

INSERT INTO system_setting (`key`, `value`, `updated_at`, `created_at`)
VALUES ('grit_meter_enabled', 'true', NOW(), NOW())
ON DUPLICATE KEY UPDATE `value` = 'true', `updated_at` = NOW();

CREATE TABLE `achievement_eligibility_grant` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `achievement_id` varchar(36) NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'pending',
  `granted_by` varchar(36) NOT NULL,
  `source` varchar(30) NOT NULL DEFAULT 'bulk_issue',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_achievement_eligibility_grant_user_achievement` (`user_id`,`achievement_id`),
  KEY `idx_achievement_eligibility_grant_achievement` (`achievement_id`),
  CONSTRAINT `fk_achievement_eligibility_grant_ref_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_achievement_eligibility_grant_ref_achievement` FOREIGN KEY (`achievement_id`) REFERENCES `achievement` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_achievement_eligibility_grant_ref_granted_by` FOREIGN KEY (`granted_by`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

ALTER TABLE `interest_group`
MODIFY COLUMN `status` ENUM('active','inactive','requested','cancelled','rejected')
NOT NULL DEFAULT 'requested';

CREATE TABLE IF NOT EXISTS `ig_media_content_link` (
  `id` varchar(36) NOT NULL,
  `media_content_id` varchar(36) NOT NULL,
  `ig_id` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ig_media_content` (`media_content_id`,`ig_id`),
  KEY `idx_ig_media_content_ig` (`ig_id`),
  CONSTRAINT `fk_ig_media_content_ref_media` FOREIGN KEY (`media_content_id`) REFERENCES `media_content` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ig_media_content_ref_ig` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `hiring` (
  `id` varchar(36) NOT NULL,
  `posted_date` date DEFAULT NULL,
  `role` varchar(255) NOT NULL,
  `organization` varchar(255) NOT NULL,
  `title` varchar(255) DEFAULT NULL,
  `location` varchar(255) DEFAULT NULL,
  `lastdate` date NOT NULL,
  `applylink` varchar(200) DEFAULT NULL,
  `jdlink` varchar(200) DEFAULT NULL,
  `duration` varchar(100) DEFAULT NULL,
  `remuneration` varchar(255) DEFAULT NULL,
  `vacancies` int unsigned DEFAULT NULL,
  `extracontent` longtext,
  `created_by_id` varchar(36) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_by_id` varchar(36) DEFAULT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_hiring_lastdate` (`lastdate`),
  KEY `idx_hiring_created_by` (`created_by_id`),
  KEY `idx_hiring_updated_by` (`updated_by_id`),
  CONSTRAINT `fk_hiring_created_by` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_hiring_updated_by` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `community_partner` (
  `id` varchar(36) NOT NULL,
  `name` varchar(150) NOT NULL,
  `logo_key` varchar(255) DEFAULT NULL,
  `description` longtext,
  `linkedin` varchar(255) DEFAULT NULL,
  `github` varchar(255) DEFAULT NULL,
  `website` varchar(255) DEFAULT NULL,
  `instagram` varchar(255) DEFAULT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_community_partner_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_community_partner_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `ig_community_partner_link` (
  `id` varchar(36) NOT NULL,
  `community_partner_id` varchar(36) NOT NULL,
  `ig_id` varchar(36) NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ig_community_partner` (`community_partner_id`,`ig_id`),
  KEY `idx_ig_community_partner_ig` (`ig_id`),
  CONSTRAINT `fk_ig_community_partner_ref_partner` FOREIGN KEY (`community_partner_id`) REFERENCES `community_partner` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ig_community_partner_ref_ig` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ig_community_partner_link_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

UPDATE system_setting SET value = '1.90', updated_at = NOW() WHERE `key` = 'db.version';

-- ---------- PART B: dev delta ----------
-- ============================================================
-- DEV DELTA: bring latest.sql (prod) up to what pranav-dev models expect
-- Generated from Django models vs latest.sql. Review before applying.
-- ============================================================

-- 1. NEW TABLES (in models, not in latest.sql)

CREATE TABLE `mentor_application` (`id` varchar(36) NOT NULL PRIMARY KEY, `user_id` varchar(36) NOT NULL, `mentor_tier` varchar(30) NOT NULL, `org_id` varchar(36) NULL, `status` varchar(30) NOT NULL, `reason` varchar(1000) NULL, `preferred_ig_ids` json NULL, `verification_note` varchar(500) NULL, `verified_by_id` varchar(36) NULL, `verified_at` datetime(6) NULL, `nomination_expires_at` datetime(6) NULL, `created_by_id` varchar(36) NOT NULL, `updated_by_id` varchar(36) NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL);

CREATE TABLE `campus_execom_role` (`id` varchar(36) NOT NULL PRIMARY KEY, `title` varchar(75) NOT NULL UNIQUE, `description` varchar(300) NULL, `created_by` varchar(36) NOT NULL, `created_at` datetime(6) NOT NULL, `updated_by` varchar(36) NOT NULL, `updated_at` datetime(6) NOT NULL);

CREATE TABLE `company_admin_link` (`id` varchar(36) NOT NULL PRIMARY KEY, `company_id` varchar(36) NOT NULL, `user_id` varchar(36) NOT NULL, `status` varchar(20) NOT NULL, `invited_by_id` varchar(36) NULL, `invited_at` datetime(6) NOT NULL, `responded_at` datetime(6) NULL, `revoked_by_id` varchar(36) NULL, `revoked_at` datetime(6) NULL, `created_by` varchar(36) NOT NULL, `updated_by` varchar(36) NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL);

CREATE TABLE `company_talent_shortlist` (`id` varchar(36) NOT NULL PRIMARY KEY, `company_id` varchar(36) NOT NULL, `user_id` varchar(36) NOT NULL, `note` varchar(500) NULL, `created_by` varchar(36) NOT NULL, `created_at` datetime(6) NOT NULL);

CREATE TABLE `company_feedback` (`id` varchar(36) NOT NULL PRIMARY KEY, `company_id` varchar(36) NOT NULL, `interaction_type` varchar(10) NOT NULL, `entity_id` varchar(36) NOT NULL, `submitted_by` varchar(36) NOT NULL, `rating` smallint UNSIGNED NOT NULL CHECK (`rating` >= 0), `comment` varchar(1000) NULL, `created_at` datetime(6) NOT NULL);

CREATE TABLE `company_collaboration` (`id` varchar(36) NOT NULL PRIMARY KEY, `company_id` varchar(36) NOT NULL, `collab_type` varchar(25) NOT NULL, `title` varchar(200) NOT NULL, `description` longtext NULL, `target_type` varchar(10) NULL, `target_org_id` varchar(36) NULL, `event_id` varchar(36) NULL, `status` varchar(10) NOT NULL, `responded_by` varchar(36) NULL, `responded_at` datetime(6) NULL, `rejection_reason` varchar(500) NULL, `created_by` varchar(36) NOT NULL, `updated_by` varchar(36) NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL);

CREATE TABLE `company_task_template` (`id` varchar(36) NOT NULL PRIMARY KEY, `company_id` varchar(36) NOT NULL, `title` varchar(75) NOT NULL, `hashtag_prefix` varchar(75) NULL, `description` longtext NULL, `karma` integer NULL, `type_id` varchar(36) NULL, `created_by` varchar(36) NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL);

CREATE TABLE `company_event_template` (`id` varchar(36) NOT NULL PRIMARY KEY, `company_id` varchar(36) NOT NULL, `title` varchar(200) NOT NULL, `description` longtext NULL, `event_type` varchar(50) NULL, `default_duration_minutes` integer NULL, `created_by` varchar(36) NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL);

CREATE TABLE `event_tag` (`id` varchar(36) NOT NULL PRIMARY KEY, `title` varchar(100) NOT NULL UNIQUE, `created_at` datetime(6) NOT NULL);

CREATE TABLE `event_tag_link` (`id` varchar(36) NOT NULL PRIMARY KEY, `event_id` varchar(36) NOT NULL, `tag_id` varchar(36) NOT NULL);

CREATE TABLE `broadcast_notification_read` (`id` char(32) NOT NULL PRIMARY KEY, `broadcast_id` char(32) NOT NULL, `user_id` varchar(36) NOT NULL, `read_at` datetime(6) NULL, `archived_at` datetime(6) NULL);


-- 2. NEW COLUMNS (in models, not in latest.sql)

ALTER TABLE `user_mentor` ADD COLUMN `is_active` bool DEFAULT b'1' NOT NULL;

ALTER TABLE `user_mentor` ALTER COLUMN `is_active` DROP DEFAULT;

ALTER TABLE `mentor_scope_grant` ADD COLUMN `application_id` varchar(36) NOT NULL , ADD CONSTRAINT `mentor_scope_grant_application_id_315a5940_fk_mentor_ap` FOREIGN KEY (`application_id`) REFERENCES `mentor_application`(`id`);

ALTER TABLE `mentor_scope_grant` ADD COLUMN `expires_at` datetime(6) NULL;

ALTER TABLE `user_settings` ADD COLUMN `active_scope_type` varchar(30) NULL;

ALTER TABLE `user_settings` ADD COLUMN `active_scope_id` varchar(36) NULL;

ALTER TABLE `interest_group` ADD COLUMN `sponsor_company_id` varchar(36) NULL , ADD CONSTRAINT `interest_group_sponsor_company_id_0ea2022a_fk_company_id` FOREIGN KEY (`sponsor_company_id`) REFERENCES `company`(`id`);

ALTER TABLE `interest_group` ADD COLUMN `sponsor_status` varchar(10) NULL;

ALTER TABLE `campus_ig_chapter` ADD COLUMN `co_lead_id` varchar(36) NULL , ADD CONSTRAINT `campus_ig_chapter_co_lead_id_e9799142_fk_user_id` FOREIGN KEY (`co_lead_id`) REFERENCES `user`(`id`);

ALTER TABLE `company` ADD COLUMN `publish_impact_report` bool DEFAULT b'0' NOT NULL;

ALTER TABLE `company` ALTER COLUMN `publish_impact_report` DROP DEFAULT;

ALTER TABLE `mentorship_session_user_link` ADD COLUMN `rating` smallint UNSIGNED NULL CHECK (`rating` >= 0);

ALTER TABLE `notification` ADD COLUMN `type` varchar(50) DEFAULT 'LEGACY' NOT NULL;

ALTER TABLE `notification` ALTER COLUMN `type` DROP DEFAULT;

ALTER TABLE `notification` ADD COLUMN `category` varchar(20) DEFAULT 'SYSTEM' NOT NULL;

ALTER TABLE `notification` ALTER COLUMN `category` DROP DEFAULT;

ALTER TABLE `notification` ADD COLUMN `context` json NULL;

ALTER TABLE `notification` ADD COLUMN `entity_type` varchar(40) NULL;

ALTER TABLE `notification` ADD COLUMN `entity_id` varchar(36) NULL;

ALTER TABLE `notification` ADD COLUMN `actor_id` varchar(36) NULL , ADD CONSTRAINT `notification_actor_id_8f11e06d_fk_user_id` FOREIGN KEY (`actor_id`) REFERENCES `user`(`id`);

ALTER TABLE `notification` ADD COLUMN `is_read` bool DEFAULT b'0' NOT NULL;

ALTER TABLE `notification` ALTER COLUMN `is_read` DROP DEFAULT;

ALTER TABLE `notification` ADD COLUMN `read_at` datetime(6) NULL;

ALTER TABLE `notification` ADD COLUMN `is_archived` bool DEFAULT b'0' NOT NULL;

ALTER TABLE `notification` ALTER COLUMN `is_archived` DROP DEFAULT;

ALTER TABLE `notification` ADD COLUMN `dedupe_key` varchar(160) NULL;

ALTER TABLE `notification` ADD COLUMN `redirect_url` varchar(255) NULL;

ALTER TABLE `notification` ADD COLUMN `batch_id` varchar(36) NULL;

ALTER TABLE `notification` ADD COLUMN `expires_at` datetime(6) NULL;

ALTER TABLE `broadcast_notification` ADD COLUMN `notif_type` varchar(50) NULL;

ALTER TABLE `broadcast_notification` ADD COLUMN `category` varchar(20) DEFAULT 'SYSTEM' NOT NULL;

ALTER TABLE `broadcast_notification` ALTER COLUMN `category` DROP DEFAULT;

ALTER TABLE `broadcast_notification` ADD COLUMN `context` json NULL;

ALTER TABLE `broadcast_notification` ADD COLUMN `entity_type` varchar(40) NULL;

ALTER TABLE `broadcast_notification` ADD COLUMN `entity_id` varchar(36) NULL;

ALTER TABLE `broadcast_notification` ADD COLUMN `actor_id` varchar(36) NULL , ADD CONSTRAINT `broadcast_notification_actor_id_b29f877e_fk_user_id` FOREIGN KEY (`actor_id`) REFERENCES `user`(`id`);

ALTER TABLE `broadcast_notification` ADD COLUMN `dedupe_key` varchar(160) NULL;

ALTER TABLE `company_jobs` ADD COLUMN `created_by` varchar(36) NULL , ADD CONSTRAINT `company_jobs_created_by_65f78c16_fk_user_id` FOREIGN KEY (`created_by`) REFERENCES `user`(`id`);

ALTER TABLE `company_jobs` ADD COLUMN `updated_by` varchar(36) NULL , ADD CONSTRAINT `company_jobs_updated_by_9d19f603_fk_user_id` FOREIGN KEY (`updated_by`) REFERENCES `user`(`id`);

ALTER TABLE `company_jobs` ADD COLUMN `approved_by` varchar(36) NULL , ADD CONSTRAINT `company_jobs_approved_by_4431582c_fk_user_id` FOREIGN KEY (`approved_by`) REFERENCES `user`(`id`);

ALTER TABLE `company_jobs` ADD COLUMN `approved_at` datetime(6) NULL;

ALTER TABLE `company_jobs` ADD COLUMN `rejection_reason` varchar(500) NULL;

ALTER TABLE `company_jobs` ADD COLUMN `expires_at` datetime(6) NULL;

ALTER TABLE `mentor_application` ADD CONSTRAINT `mentor_application_user_id_88a9d675_fk_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`);

ALTER TABLE `mentor_application` ADD CONSTRAINT `mentor_application_org_id_4ba2cb44_fk_organization_id` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`);

ALTER TABLE `mentor_application` ADD CONSTRAINT `mentor_application_verified_by_id_b03adf9c_fk_user_id` FOREIGN KEY (`verified_by_id`) REFERENCES `user` (`id`);

ALTER TABLE `mentor_application` ADD CONSTRAINT `mentor_application_created_by_id_7aa822b7_fk_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`);

ALTER TABLE `mentor_application` ADD CONSTRAINT `mentor_application_updated_by_id_953c6ac0_fk_user_id` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`);

ALTER TABLE `campus_execom_role` ADD CONSTRAINT `campus_execom_role_created_by_f34446a2_fk_user_id` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`);

ALTER TABLE `campus_execom_role` ADD CONSTRAINT `campus_execom_role_updated_by_7f6e3f8c_fk_user_id` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`);

ALTER TABLE `company_admin_link` ADD CONSTRAINT `company_admin_link_company_id_user_id_e36e5b59_uniq` UNIQUE (`company_id`, `user_id`);

ALTER TABLE `company_admin_link` ADD CONSTRAINT `company_admin_link_company_id_b82d7cc0_fk_company_id` FOREIGN KEY (`company_id`) REFERENCES `company` (`id`);

ALTER TABLE `company_admin_link` ADD CONSTRAINT `company_admin_link_user_id_299ab86b_fk_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`);

ALTER TABLE `company_admin_link` ADD CONSTRAINT `company_admin_link_invited_by_id_fbc3158d_fk_user_id` FOREIGN KEY (`invited_by_id`) REFERENCES `user` (`id`);

ALTER TABLE `company_admin_link` ADD CONSTRAINT `company_admin_link_revoked_by_id_f64cd1d0_fk_user_id` FOREIGN KEY (`revoked_by_id`) REFERENCES `user` (`id`);

ALTER TABLE `company_admin_link` ADD CONSTRAINT `company_admin_link_created_by_85ba316d_fk_user_id` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`);

ALTER TABLE `company_admin_link` ADD CONSTRAINT `company_admin_link_updated_by_3f31880d_fk_user_id` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`);

ALTER TABLE `company_talent_shortlist` ADD CONSTRAINT `company_talent_shortlist_company_id_user_id_3009341d_uniq` UNIQUE (`company_id`, `user_id`);

ALTER TABLE `company_talent_shortlist` ADD CONSTRAINT `company_talent_shortlist_company_id_5da8dd98_fk_company_id` FOREIGN KEY (`company_id`) REFERENCES `company` (`id`);

ALTER TABLE `company_talent_shortlist` ADD CONSTRAINT `company_talent_shortlist_user_id_72956927_fk_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`);

ALTER TABLE `company_talent_shortlist` ADD CONSTRAINT `company_talent_shortlist_created_by_7b0e82a4_fk_user_id` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`);

ALTER TABLE `company_feedback` ADD CONSTRAINT `company_feedback_company_id_interaction_t_7a452baf_uniq` UNIQUE (`company_id`, `interaction_type`, `entity_id`, `submitted_by`);

ALTER TABLE `company_feedback` ADD CONSTRAINT `company_feedback_company_id_8da1797c_fk_company_id` FOREIGN KEY (`company_id`) REFERENCES `company` (`id`);

ALTER TABLE `company_feedback` ADD CONSTRAINT `company_feedback_submitted_by_9af8450d_fk_user_id` FOREIGN KEY (`submitted_by`) REFERENCES `user` (`id`);

ALTER TABLE `company_collaboration` ADD CONSTRAINT `company_collaboration_company_id_85bc7d06_fk_company_id` FOREIGN KEY (`company_id`) REFERENCES `company` (`id`);

ALTER TABLE `company_collaboration` ADD CONSTRAINT `company_collaboration_event_id_64346b2c_fk_events_id` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`);

ALTER TABLE `company_collaboration` ADD CONSTRAINT `company_collaboration_responded_by_1124d23c_fk_user_id` FOREIGN KEY (`responded_by`) REFERENCES `user` (`id`);

ALTER TABLE `company_collaboration` ADD CONSTRAINT `company_collaboration_created_by_4711277b_fk_user_id` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`);

ALTER TABLE `company_collaboration` ADD CONSTRAINT `company_collaboration_updated_by_efcfabc8_fk_user_id` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`);

ALTER TABLE `company_task_template` ADD CONSTRAINT `company_task_template_company_id_fe6477a3_fk_company_id` FOREIGN KEY (`company_id`) REFERENCES `company` (`id`);

ALTER TABLE `company_task_template` ADD CONSTRAINT `company_task_template_type_id_d79a426e_fk_task_type_id` FOREIGN KEY (`type_id`) REFERENCES `task_type` (`id`);

ALTER TABLE `company_task_template` ADD CONSTRAINT `company_task_template_created_by_ceb6c374_fk_user_id` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`);

ALTER TABLE `company_event_template` ADD CONSTRAINT `company_event_template_company_id_9f3a2352_fk_company_id` FOREIGN KEY (`company_id`) REFERENCES `company` (`id`);

ALTER TABLE `company_event_template` ADD CONSTRAINT `company_event_template_created_by_c83ca945_fk_user_id` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`);

ALTER TABLE `event_tag_link` ADD CONSTRAINT `event_tag_link_event_id_tag_id_85f62efd_uniq` UNIQUE (`event_id`, `tag_id`);

ALTER TABLE `event_tag_link` ADD CONSTRAINT `event_tag_link_event_id_e5205f5e_fk_events_id` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`);

ALTER TABLE `event_tag_link` ADD CONSTRAINT `event_tag_link_tag_id_82ecbb47_fk_event_tag_id` FOREIGN KEY (`tag_id`) REFERENCES `event_tag` (`id`);

ALTER TABLE `broadcast_notification_read` ADD CONSTRAINT `broadcast_notificati_broadcast_id_d5de6f07_fk_broadcast` FOREIGN KEY (`broadcast_id`) REFERENCES `broadcast_notification` (`id`);

ALTER TABLE `broadcast_notification_read` ADD CONSTRAINT `broadcast_notification_read_user_id_d8838ad9_fk_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`);


-- 3. COLUMN FIXES (existing columns that conflict with models)

-- user_mentor.expertise: text -> longtext
ALTER TABLE `user_mentor` MODIFY COLUMN `expertise` longtext NULL;

-- user_mentor.hours: model allows NULL; type int -> varchar(20)
ALTER TABLE `user_mentor` MODIFY COLUMN `hours` varchar(20) NULL DEFAULT NULL;

-- mentor_scope_grant.scope_type: widen varchar(14) -> varchar(30)
ALTER TABLE `mentor_scope_grant` MODIFY COLUMN `scope_type` varchar(30) NOT NULL;

-- socials.linkedin: widen varchar(60) -> varchar(255)
ALTER TABLE `socials` MODIFY COLUMN `linkedin` varchar(255) NULL DEFAULT NULL;

-- socials.updated_at: model allows NULL
ALTER TABLE `socials` MODIFY COLUMN `updated_at` datetime NULL DEFAULT NULL;

-- user_organization_link.is_alumni: model allows NULL
ALTER TABLE `user_organization_link` MODIFY COLUMN `is_alumni` tinyint(1) NULL DEFAULT '0';

-- enabler_campus_note.note: text -> longtext
ALTER TABLE `enabler_campus_note` MODIFY COLUMN `note` longtext NOT NULL;

-- college_showcase.about: text -> longtext
ALTER TABLE `college_showcase` MODIFY COLUMN `about` longtext NULL;

-- interest_group.code: widen varchar(5) -> varchar(10)
ALTER TABLE `interest_group` MODIFY COLUMN `code` varchar(10) NOT NULL;

-- interest_group.about: text -> longtext
ALTER TABLE `interest_group` MODIFY COLUMN `about` longtext NULL;

-- interest_group.prerequisites: text -> longtext
ALTER TABLE `interest_group` MODIFY COLUMN `prerequisites` longtext NULL;

-- interest_group.career_opportunities: text -> longtext
ALTER TABLE `interest_group` MODIFY COLUMN `career_opportunities` longtext NULL;

-- interest_group.top_blogs: text -> longtext
ALTER TABLE `interest_group` MODIFY COLUMN `top_blogs` longtext NULL;

-- interest_group.people_to_follow: text -> longtext
ALTER TABLE `interest_group` MODIFY COLUMN `people_to_follow` longtext NULL;

-- interest_group.resource: text -> longtext
ALTER TABLE `interest_group` MODIFY COLUMN `resource` longtext NULL;

-- interest_group.leads: text -> longtext
ALTER TABLE `interest_group` MODIFY COLUMN `leads` longtext NULL;

-- interest_group.mentors: text -> longtext
ALTER TABLE `interest_group` MODIFY COLUMN `mentors` longtext NULL;

-- interest_group.thinktank: text -> longtext
ALTER TABLE `interest_group` MODIFY COLUMN `thinktank` longtext NULL;

-- task_list.description: text -> longtext
ALTER TABLE `task_list` MODIFY COLUMN `description` longtext NULL;

-- task_list.rejection_reason: text -> longtext
ALTER TABLE `task_list` MODIFY COLUMN `rejection_reason` longtext NULL;

-- wallet.karma_last_updated_at: model allows NULL
ALTER TABLE `wallet` MODIFY COLUMN `karma_last_updated_at` datetime NULL DEFAULT NULL;

-- karma_activity_log.user_id: model allows NULL
ALTER TABLE `karma_activity_log` MODIFY COLUMN `user_id` varchar(36) NULL DEFAULT NULL;

-- voucher_log.code: widen varchar(15) -> varchar(255)
ALTER TABLE `voucher_log` MODIFY COLUMN `code` varchar(255) NOT NULL;

-- categories.description: text -> longtext
ALTER TABLE `categories` MODIFY COLUMN `description` longtext NULL;

-- campus_ig_chapter.description: text -> longtext
ALTER TABLE `campus_ig_chapter` MODIFY COLUMN `description` longtext NULL;

-- campus_social_link.platform: widen varchar(20) -> varchar(30)
ALTER TABLE `campus_social_link` MODIFY COLUMN `platform` varchar(30) NOT NULL;

-- comic.description: text -> longtext
ALTER TABLE `comic` MODIFY COLUMN `description` longtext NULL;

-- chapter.description: text -> longtext
ALTER TABLE `chapter` MODIFY COLUMN `description` longtext NULL;

-- comic_comment.message: text -> longtext
ALTER TABLE `comic_comment` MODIFY COLUMN `message` longtext NOT NULL;

-- company.logo: text -> longtext
ALTER TABLE `company` MODIFY COLUMN `logo` longtext NULL;

-- company.description: text -> longtext
ALTER TABLE `company` MODIFY COLUMN `description` longtext NOT NULL;

-- company.website_link: text -> longtext
ALTER TABLE `company` MODIFY COLUMN `website_link` longtext NULL;

-- company.linkedin_url: text -> longtext
ALTER TABLE `company` MODIFY COLUMN `linkedin_url` longtext NULL;

-- company.verification_document_url: text -> longtext
ALTER TABLE `company` MODIFY COLUMN `verification_document_url` longtext NULL;

-- company.rejection_reason: text -> longtext
ALTER TABLE `company` MODIFY COLUMN `rejection_reason` longtext NULL;

-- company.culture_text: text -> longtext
ALTER TABLE `company` MODIFY COLUMN `culture_text` longtext NULL;

-- donor.address: text -> longtext
ALTER TABLE `donor` MODIFY COLUMN `address` longtext NULL;

-- donation.proof_url: text -> longtext
ALTER TABLE `donation` MODIFY COLUMN `proof_url` longtext NULL;

-- events.description: text -> longtext
ALTER TABLE `events` MODIFY COLUMN `description` longtext NULL;

-- media_content.description: text -> longtext
ALTER TABLE `media_content` MODIFY COLUMN `description` longtext NULL;

-- hackathon_submission.data: model allows NULL; type varchar(2000) -> json
ALTER TABLE `hackathon_submission` MODIFY COLUMN `data` json NULL;

-- impact_project.description: text -> longtext
ALTER TABLE `impact_project` MODIFY COLUMN `description` longtext NOT NULL;

-- launchpad_companies.description: text -> longtext
ALTER TABLE `launchpad_companies` MODIFY COLUMN `description` longtext NULL;

-- launchpad_job_tasks.task_description: text -> longtext
ALTER TABLE `launchpad_job_tasks` MODIFY COLUMN `task_description` longtext NOT NULL;

-- launchpad_job_applications.cover_letter: text -> longtext
ALTER TABLE `launchpad_job_applications` MODIFY COLUMN `cover_letter` longtext NULL;

-- learning_circle.description: model allows NULL
ALTER TABLE `learning_circle` MODIFY COLUMN `description` varchar(1000) NULL DEFAULT NULL;

-- circle_meeting_log.meet_code: model allows NULL; widen varchar(6) -> varchar(10)
ALTER TABLE `circle_meeting_log` MODIFY COLUMN `meet_code` varchar(10) NULL DEFAULT NULL;

-- circle_meeting_log.meet_link: widen varchar(100) -> varchar(200)
ALTER TABLE `circle_meeting_log` MODIFY COLUMN `meet_link` varchar(200) NULL DEFAULT NULL;

-- mentorship_session.description: text -> longtext
ALTER TABLE `mentorship_session` MODIFY COLUMN `description` longtext NULL;

-- mentorship_session_user_link.feedback: text -> longtext
ALTER TABLE `mentorship_session_user_link` MODIFY COLUMN `feedback` longtext NULL;

-- ig_opportunity.description: text -> longtext
ALTER TABLE `ig_opportunity` MODIFY COLUMN `description` longtext NOT NULL;

-- ig_opportunity.eligibility: text -> longtext
ALTER TABLE `ig_opportunity` MODIFY COLUMN `eligibility` longtext NULL;

-- notification.title: widen varchar(50) -> varchar(100)
ALTER TABLE `notification` MODIFY COLUMN `title` varchar(100) NOT NULL;

-- notification.description: widen varchar(200) -> varchar(300)
ALTER TABLE `notification` MODIFY COLUMN `description` varchar(300) NOT NULL;

-- broadcast_notification.title: widen varchar(50) -> varchar(100)
ALTER TABLE `broadcast_notification` MODIFY COLUMN `title` varchar(100) NOT NULL;

-- broadcast_notification.description: widen varchar(200) -> varchar(300)
ALTER TABLE `broadcast_notification` MODIFY COLUMN `description` varchar(300) NOT NULL;

-- skill.description: text -> longtext
ALTER TABLE `skill` MODIFY COLUMN `description` longtext NULL;

-- projects.description: text -> longtext
ALTER TABLE `projects` MODIFY COLUMN `description` longtext NOT NULL;

-- projects_comments.comment: text -> longtext
ALTER TABLE `projects_comments` MODIFY COLUMN `comment` longtext NOT NULL;

-- url_shortener.count: model allows NULL
ALTER TABLE `url_shortener` MODIFY COLUMN `count` int NULL DEFAULT '0';

-- company_jobs.job_description: text -> longtext
ALTER TABLE `company_jobs` MODIFY COLUMN `job_description` longtext NULL;

-- user_job_application.resume_link: text -> longtext
ALTER TABLE `user_job_application` MODIFY COLUMN `resume_link` longtext NULL;

-- user_job_application.cover_letter: text -> longtext
ALTER TABLE `user_job_application` MODIFY COLUMN `cover_letter` longtext NULL;

-- user_job_application.rejection_reason: text -> longtext
ALTER TABLE `user_job_application` MODIFY COLUMN `rejection_reason` longtext NULL;


-- ============================================================
-- DELTA PART 2 (found after loading ALL model modules, incl. db/intern.py and db/community_partner.py)
-- ============================================================

-- 3b. COLUMN FIXES for intern tables (TEXT -> LONGTEXT)

-- intern_task.description: text -> longtext
ALTER TABLE `intern_task` MODIFY COLUMN `description` longtext NOT NULL;

-- intern_daily_timesheet.description: text -> longtext
ALTER TABLE `intern_daily_timesheet` MODIFY COLUMN `description` longtext NOT NULL;

-- intern_daily_timesheet.blockers: text -> longtext
ALTER TABLE `intern_daily_timesheet` MODIFY COLUMN `blockers` longtext NULL;

-- intern_daily_timesheet.end_of_day_note: text -> longtext
ALTER TABLE `intern_daily_timesheet` MODIFY COLUMN `end_of_day_note` longtext NULL;

-- intern_weekly_review.weekly_review: text -> longtext
ALTER TABLE `intern_weekly_review` MODIFY COLUMN `weekly_review` longtext NOT NULL;

-- intern_weekly_review.blockers: text -> longtext
ALTER TABLE `intern_weekly_review` MODIFY COLUMN `blockers` longtext NULL;

-- intern_weekly_review.leave_days: text -> longtext
ALTER TABLE `intern_weekly_review` MODIFY COLUMN `leave_days` longtext NULL;

-- intern_weekly_review.suggestions: text -> longtext
ALTER TABLE `intern_weekly_review` MODIFY COLUMN `suggestions` longtext NULL;

-- intern_leave_request.reason: text -> longtext
ALTER TABLE `intern_leave_request` MODIFY COLUMN `reason` longtext NOT NULL;

-- 4. ENUM COLUMNS missing values the models use (existing values kept, new ones added)

-- system_action_log.action_type: add ['MENTOR_APP_SUBMITTED', 'MENTOR_DEACTIVATE', 'DELEGATE_INVITED', 'DELEGATE_RESPONDED', 'DELEGATE_REVOKED', 'MENTOR_REACTIVATE', 'MENTOR_APPLY', 'MENTOR_NOMINATE', 'COMPANY_MENTOR_VERIFY', 'JOB_APPROVE', 'JOB_REJECT', 'COMPANY_EVENT_APPROVE', 'COMPANY_EVENT_REJECT', 'CAMPUS_EVENT_APPROVE', 'CAMPUS_EVENT_REJECT', 'IG_EVENT_APPROVE', 'IG_EVENT_REJECT', 'IMPACT_PROJECT_PUBLISH', 'COMPANY_DEACTIVATED']
ALTER TABLE `system_action_log` MODIFY COLUMN `action_type` enum('PERSONA_SWITCH','TASK_REVIEW','EVENT_REVIEW','SESSION_CREATE','SESSION_UPDATE','SESSION_STATUS','KARMA_AWARD','MANUAL_HOURS_LOG','IG_CONTENT_UPDATE','OPPORTUNITY_POST','MENTOR_VERIFY','INTERN_TASK_UPDATE','INTERN_LEAVE_REQUEST','INTERN_LEAVE_REVIEW','INTERN_TIMESHEET_EDIT','INTERN_GUILD_REASSIGN','MENTOR_APP_SUBMITTED','MENTOR_DEACTIVATE','DELEGATE_INVITED','DELEGATE_RESPONDED','DELEGATE_REVOKED','MENTOR_REACTIVATE','MENTOR_APPLY','MENTOR_NOMINATE','COMPANY_MENTOR_VERIFY','JOB_APPROVE','JOB_REJECT','COMPANY_EVENT_APPROVE','COMPANY_EVENT_REJECT','CAMPUS_EVENT_APPROVE','CAMPUS_EVENT_REJECT','IG_EVENT_APPROVE','IG_EVENT_REJECT','IMPACT_PROJECT_PUBLISH','COMPANY_DEACTIVATED') NOT NULL;

-- company_jobs.status: add ['Pending Approval', 'Needs Revision', 'Rejected']
ALTER TABLE `company_jobs` MODIFY COLUMN `status` enum('Draft','Active','Closed','Expired','Pending Approval','Needs Revision','Rejected') NOT NULL DEFAULT 'Draft';


-- 5. PROD-ONLY NOT NULL COLUMNS the models do not know about (inserts from the app would fail)

ALTER TABLE `donor` MODIFY COLUMN `payment_id` varchar(100) NULL DEFAULT NULL;

ALTER TABLE `donor` MODIFY COLUMN `payment_method` varchar(100) NULL DEFAULT NULL;

ALTER TABLE `donor` MODIFY COLUMN `amount` float NULL DEFAULT NULL;

ALTER TABLE `donor` MODIFY COLUMN `currency` varchar(30) NULL DEFAULT NULL;

ALTER TABLE `intern_daily_timesheet` MODIFY COLUMN `category` varchar(50) NULL DEFAULT NULL;

ALTER TABLE `mentor_scope_grant` MODIFY COLUMN `mentor_id` varchar(36) NULL DEFAULT NULL;

ALTER TABLE `voucher_log` MODIFY COLUMN `mail` varchar(200) NULL DEFAULT NULL;


-- ---------- PART C: company problem statements (alter-1.91) ----------

CREATE TABLE IF NOT EXISTS `problem_statement` (
  `id` char(36) NOT NULL,
  `company_id` char(36) NOT NULL,
  `title` varchar(150) NOT NULL,
  `description` text NOT NULL,
  `category` varchar(100) NOT NULL,
  `skills` json NOT NULL,
  `deadline` datetime(6) DEFAULT NULL,
  `status` enum('Draft','Published','Unpublished') NOT NULL DEFAULT 'Draft',
  `created_by` char(36) NOT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_by` char(36) NOT NULL,
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  `published_by` char(36) DEFAULT NULL,
  `published_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_problem_statement_company_status_updated` (`company_id`,`status`,`updated_at`),
  KEY `idx_problem_statement_status_published` (`status`,`published_at`),
  KEY `idx_problem_statement_created_by` (`created_by`),
  KEY `idx_problem_statement_updated_by` (`updated_by`),
  KEY `idx_problem_statement_published_by` (`published_by`),
  CONSTRAINT `fk_problem_statement_ref_company` FOREIGN KEY (`company_id`) REFERENCES `company` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_problem_statement_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_problem_statement_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_problem_statement_ref_published_by` FOREIGN KEY (`published_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `chk_problem_statement_skills` CHECK (json_type(`skills`) = 'ARRAY')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `problem_statement_interaction` (
  `id` char(36) NOT NULL,
  `problem_statement_id` char(36) NOT NULL,
  `user_id` char(36) NOT NULL,
  `status` enum('Trying') NOT NULL DEFAULT 'Trying',
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_problem_statement_interaction_statement_user` (`problem_statement_id`,`user_id`),
  KEY `idx_problem_statement_interaction_statement_status` (`problem_statement_id`,`status`),
  KEY `idx_problem_statement_interaction_user` (`user_id`),
  CONSTRAINT `fk_problem_statement_interaction_ref_statement` FOREIGN KEY (`problem_statement_id`) REFERENCES `problem_statement` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_problem_statement_interaction_ref_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
