import os
import sys
import uuid
from decouple import config
import django

from connection import execute

os.chdir("..")
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mulearnbackend.settings")
django.setup()


def get_recurring_lc_ids():
    query = "SELECT id, day from learning_circle where day is not null"
    return execute(query)


def migrate_to_new_lc():
    lcs = get_recurring_lc_ids()
    execute("DROP TABLE IF EXISTS circle_meet_attendee_report;")
    execute("DROP TABLE IF EXISTS circle_meet_attendees;")
    execute("DROP TABLE IF EXISTS circle_meet_tasks;")
    execute("DROP TABLE IF EXISTS circle_meeting_log;")
    execute(
        """
ALTER TABLE learning_circle
    MODIFY COLUMN name VARCHAR(255),
    MODIFY COLUMN circle_code VARCHAR(15),
    DROP COLUMN meet_time,
    DROP COLUMN day,
    DROP COLUMN meet_place,
    DROP FOREIGN KEY fk_learning_circle_ref_updated_by,
    DROP COLUMN updated_by,
    ADD COLUMN is_recurring BOOLEAN DEFAULT FALSE NOT NULL,
    ADD COLUMN recurrence_type VARCHAR(10),
    ADD COLUMN recurrence      INT;
"""
    )
    execute(
        """
CREATE TABLE circle_meeting_log
(
    id                  VARCHAR(36) PRIMARY KEY NOT NULL,
    circle_id           VARCHAR(36)             NOT NULL,
    meet_code           VARCHAR(6)              NOT NULL,
    title               VARCHAR(100)            NOT NULL,
    is_report_needed    BOOLEAN DEFAULT TRUE NOT NULL,
    report_description  VARCHAR(1000),
    coord_x             FLOAT NOT NULL          NOT NULL,
    coord_y             FLOAT NOT NULL          NOT NULL,
    meet_place          VARCHAR(255)            NOT NULL,
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
"""
    )
    execute(
        """
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
"""
    )
    for id, day in lcs:
        day = str(day).split(",")[0]
        query = f"""UPDATE learning_circle SET is_recurring = TRUE, recurrence_type = 'weekly', recurrence = {day} WHERE id = '{id}'"""
        execute(query)


if __name__ == "__main__":
    migrate_to_new_lc()
    execute(
        "UPDATE system_setting SET value = '1.59', updated_at = now() WHERE `key` = 'db.version';"
    )
