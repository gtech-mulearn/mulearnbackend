import os
import sys
import uuid
import django

from connection import execute

os.chdir("..")
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mulearnbackend.settings")
django.setup()
from utils.utils import generate_code

from django.db.transaction import atomic


def get_circle_meeting_logs():
    query = (
        f"SELECT id, attendees, created_at, updated_at, images FROM circle_meeting_log"
    )
    return execute(query)


def create_attendees_table():
    query = """CREATE TABLE circle_meet_attendees (
        id          VARCHAR(36) PRIMARY KEY NOT NULL,
        meet_id     VARCHAR(36) NOT NULL,
        user_id     VARCHAR(36) NOT NULL,
        note        VARCHAR(1000),
        joined_at   DATETIME,
        approved_by VARCHAR(36),
        created_at  DATETIME    NOT NULL,
        updated_at  DATETIME    NOT NULL,
        CONSTRAINT fk_circle_meet_attendees_meet_id FOREIGN KEY (meet_id) REFERENCES circle_meeting_log(id),
        CONSTRAINT fk_circle_meet_attendees_user_id FOREIGN KEY (user_id) REFERENCES user(id),
        CONSTRAINT fk_circle_meet_attendees_approved_by FOREIGN KEY (approved_by) REFERENCES user(id)
    )"""
    execute(query)


def migrate_attendees_to_table():
    for meet_id, attendees, created_at, updated_at, images in get_circle_meeting_logs():
        attendees = (attendees if attendees else "").split(",")
        meet_code = "OLD" + generate_code(3)
        query = f"UPDATE circle_meeting_log SET meet_code = '{meet_code}', is_started = {int(images is not None)}, is_report_submitted = {int(images is not None)} WHERE id = '{meet_id}'"
        execute(query)
        for attendee in attendees:
            query = f"""
            INSERT INTO circle_meet_attendees (id, meet_id, user_id, joined_at, approved_by, created_at, updated_at) VALUES 
            ('{str(uuid.uuid4())}', '{meet_id}', '{attendee}', '{updated_at}', '{attendee}', '{created_at}', '{updated_at}');
            """
            execute(query)


if __name__ == "__main__":
    with atomic():
        create_attendees_table()
        execute(
            """
                ALTER TABLE circle_meeting_log 
                    MODIFY COLUMN `day` VARCHAR(20),
                    ADD COLUMN title VARCHAR(100) NOT NULL AFTER circle_id,
                    ADD COLUMN location VARCHAR(200) NOT NULL AFTER meet_place,
                    ADD COLUMN meet_code VARCHAR(6) NOT NULL AFTER id,
                    ADD COLUMN pre_requirements VARCHAR(1000) AFTER agenda,
                    ADD COLUMN is_public BOOLEAN DEFAULT TRUE NOT NULL AFTER pre_requirements,
                    ADD COLUMn max_attendees INT DEFAULT -1 AFTER pre_requirements,
                    ADD COLUMN is_started BOOLEAN DEFAULT FALSE NOT NULL AFTER max_attendees,
                    ADD COLUMN report_text VARCHAR(1000) AFTER max_attendees,
                    ADD COLUMN is_report_submitted BOOLEAN DEFAULT FALSE NOT NULL AFTER report_text
            """
        )
        migrate_attendees_to_table()
        execute("ALTER TABLE circle_meeting_log DROP COLUMN attendees")
        execute(
            "UPDATE system_setting SET value = '1.55', updated_at = now() WHERE `key` = 'db.version';"
        )
