import os
import sys
from pathlib import Path
from decouple import config
import django

from connection import execute

BASE_DIR = Path(__file__).resolve().parent.parent
os.chdir(BASE_DIR)
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mulearnbackend.settings')
django.setup()

DB_NAME = config('DATABASE_NAME')


def get_column_type(table_name, column_name):
    query = f"""
        SELECT DATA_TYPE FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = '{DB_NAME}' AND TABLE_NAME = '{table_name}' AND COLUMN_NAME = '{column_name}';
    """
    result = execute(query)
    return result[0][0] if result else None


def migrate_user_mentor_hours():
    """
    `user_mentor.hours` was an `int NOT NULL` (0-based count of weekly
    hours). It's now an optional free-choice bucket (e.g. "0-1 hours"),
    stored as a short code ('0-1', '1-2', '2-5', '5-10', '10+') matching
    db.user.UserMentor.HoursCommitment. Converts existing numeric values
    into the closest bucket, then relaxes the column to a nullable varchar
    so mentors can leave it unset.
    """
    current_type = get_column_type('user_mentor', 'hours')

    if current_type is None:
        print("[alter-1.64] Column 'user_mentor.hours' not found. Skipping.")
        return

    if current_type != 'int':
        print(f"[alter-1.64] Column 'user_mentor.hours' is already '{current_type}'. Skipping.")
        return

    # 1. Add the new text column alongside the old numeric one.
    execute("ALTER TABLE `user_mentor` ADD COLUMN `hours_bucket` VARCHAR(20) DEFAULT NULL;")
    print("[alter-1.64] Added temporary column 'hours_bucket'.")

    # 2. Bucket existing numeric values into the new ranges. A stored 0
    # (the old field's default for "unset") becomes NULL rather than
    # '0-1', since it never represented a deliberate choice.
    execute("""
        UPDATE `user_mentor` SET `hours_bucket` = CASE
            WHEN `hours` IS NULL OR `hours` = 0 THEN NULL
            WHEN `hours` <= 1 THEN '0-1'
            WHEN `hours` <= 2 THEN '1-2'
            WHEN `hours` <= 5 THEN '2-5'
            WHEN `hours` <= 10 THEN '5-10'
            ELSE '10+'
        END;
    """)
    print("[alter-1.64] Backfilled 'hours_bucket' from existing numeric 'hours' values.")

    # 3. Drop the old numeric column and put the new one in its place.
    execute("ALTER TABLE `user_mentor` DROP COLUMN `hours`;")
    execute("ALTER TABLE `user_mentor` CHANGE COLUMN `hours_bucket` `hours` VARCHAR(20) DEFAULT NULL;")
    print("[alter-1.64] Replaced 'user_mentor.hours' with a nullable VARCHAR(20) bucket column.")


if __name__ == '__main__':
    migrate_user_mentor_hours()
    execute("UPDATE system_setting SET value = '1.64', updated_at = now() WHERE `key` = 'db.version';")
    print("[alter-1.64] Updated database version to 1.64.")
