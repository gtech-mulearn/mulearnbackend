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

def table_exists(table_name):
    query = f"SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{DB_NAME}' AND TABLE_NAME = '{table_name}';"
    result = execute(query)
    return result and result[0][0] > 0

def column_exists(table_name, column_name):
    query = f"""
        SELECT COUNT(*) FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = '{DB_NAME}' AND TABLE_NAME = '{table_name}' AND COLUMN_NAME = '{column_name}';
    """
    result = execute(query)
    return result and result[0][0] > 0

def get_fk_constraint_name(table, column):
    query = f"""
        SELECT CONSTRAINT_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = '{DB_NAME}'
          AND TABLE_NAME = '{table}'
          AND COLUMN_NAME = '{column}'
          AND REFERENCED_TABLE_NAME IS NOT NULL;
    """
    result = execute(query)
    return result[0][0] if result else None


def migrate_mentor_tables():
    # Check if the full migration has already completed.
    if not table_exists('user_mentor_old') and not column_exists('user_mentor', 'mentor_tier'):
        print("[alter-1.63] Migration appears to be fully complete. Skipping.")
        return

    # 1. Create the new mentor_application table
    if not table_exists('mentor_application'):
        execute("""
            CREATE TABLE `mentor_application` (
          `id` CHAR(36) NOT NULL,
          `user_id` CHAR(36) NOT NULL,
          `mentor_tier` VARCHAR(30) NOT NULL,
          `org_id` CHAR(36) DEFAULT NULL,
          `status` VARCHAR(30) NOT NULL DEFAULT 'PENDING',
          `reason` VARCHAR(1000) DEFAULT NULL,
          `preferred_ig_ids` JSON DEFAULT NULL,
          `verification_note` VARCHAR(500) DEFAULT NULL,
          `verified_by_id` CHAR(36) DEFAULT NULL,
          `verified_at` DATETIME(6) DEFAULT NULL,
          `created_by_id` CHAR(36) NOT NULL,
          `updated_by_id` CHAR(36) NOT NULL,
          `created_at` DATETIME(6) NOT NULL,
          `updated_at` DATETIME(6) NOT NULL,
          PRIMARY KEY (`id`),
          KEY `fk_mentor_application_ref_user_id` (`user_id`),
          KEY `fk_mentor_application_ref_org_id` (`org_id`),
          KEY `fk_mentor_application_ref_verified_by` (`verified_by_id`),
          CONSTRAINT `fk_mentor_application_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
          CONSTRAINT `fk_mentor_application_ref_org_id` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`) ON DELETE SET NULL,
          CONSTRAINT `fk_mentor_application_ref_verified_by` FOREIGN KEY (`verified_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """)
        print("[alter-1.63] Created table 'mentor_application'.")
    else:
        print("[alter-1.63] Table 'mentor_application' already exists. Skipping creation.")

    # 2. Rename old user_mentor table
    if column_exists('user_mentor', 'mentor_tier'):
        execute("RENAME TABLE `user_mentor` TO `user_mentor_old`;")
        print("[alter-1.63] Renamed 'user_mentor' to 'user_mentor_old'.")
    else:
        print("[alter-1.63] 'user_mentor' does not have old structure. Skipping rename.")

    # 3. Create the new, simplified user_mentor table for profiles
    if not table_exists('user_mentor'):
        execute("""
            CREATE TABLE `user_mentor` (
          `id` varchar(36) NOT NULL,
          `user_id` varchar(36) NOT NULL,
          `about` varchar(1000) DEFAULT NULL,
          `expertise` text,
          `hours` int NOT NULL,
          `updated_by` varchar(36) NOT NULL,
          `updated_at` datetime(6) DEFAULT NULL,
          `created_by` varchar(36) NOT NULL,
          `created_at` datetime(6) DEFAULT NULL,
          PRIMARY KEY (`id`),
          UNIQUE KEY `user_mentor_profile_user_id_unique` (`user_id`),
          CONSTRAINT `fk_user_mentor_profile_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
          CONSTRAINT `fk_user_mentor_profile_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
          CONSTRAINT `fk_user_mentor_profile_ref_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """)
        print("[alter-1.63] Created new simplified 'user_mentor' table.")
    else:
        print("[alter-1.63] Table 'user_mentor' already exists. Skipping creation.")

    # 4 & 5. Populate new tables if the old one exists
    if table_exists('user_mentor_old'):
        execute("""
            INSERT INTO `user_mentor` (id, user_id, about, expertise, hours, updated_by, updated_at, created_by, created_at)
            SELECT UUID(), t.user_id, t.about, t.expertise, t.hours, t.updated_by, t.updated_at, t.created_by, t.created_at
            FROM `user_mentor_old` t
            INNER JOIN (
                SELECT user_id, MAX(updated_at) as max_updated_at FROM `user_mentor_old` GROUP BY user_id
            ) tm ON t.user_id = tm.user_id AND t.updated_at = tm.max_updated_at
            ON DUPLICATE KEY UPDATE
                about = VALUES(about), expertise = VALUES(expertise), hours = VALUES(hours),
                updated_by = VALUES(updated_by), updated_at = VALUES(updated_at);
        """)
        print("[alter-1.63] Migrated data to new 'user_mentor' profile table.")

        app_count_res = execute("SELECT COUNT(*) FROM mentor_application;")
        if not app_count_res or app_count_res[0][0] == 0:
            execute("""
                INSERT INTO `mentor_application` (id, user_id, mentor_tier, org_id, status, reason, preferred_ig_ids, verification_note, verified_by_id, verified_at, created_by_id, updated_by_id, created_at, updated_at)
                SELECT id, user_id, mentor_tier, org_id, status, reason, preferred_ig_ids, verification_note, verified_by, verified_at, created_by, updated_by, created_at, updated_at
                FROM `user_mentor_old`;
            """)
            print("[alter-1.63] Migrated data to 'mentor_application' table.")
        else:
            print("[alter-1.63] Table 'mentor_application' seems populated. Skipping data migration.")
    else:
        print("[alter-1.63] 'user_mentor_old' not found. Skipping data migration steps.")

    # 6. Update mentor_scope_grant to point to mentor_application
    if column_exists('mentor_scope_grant', 'mentor_id'):
        fk_name = get_fk_constraint_name('mentor_scope_grant', 'mentor_id')
        if fk_name:
            execute(f"ALTER TABLE `mentor_scope_grant` DROP FOREIGN KEY `{fk_name}`;")
            print(f"[alter-1.63] Dropped foreign key '{fk_name}' from 'mentor_scope_grant'.")

        execute("ALTER TABLE `mentor_scope_grant` CHANGE COLUMN `mentor_id` `application_id` VARCHAR(36) NOT NULL;")
        execute("ALTER TABLE `mentor_scope_grant` ADD CONSTRAINT `fk_mentor_scope_grant_ref_application_id` FOREIGN KEY (`application_id`) REFERENCES `mentor_application`(`id`) ON DELETE CASCADE;")
        print("[alter-1.63] Updated 'mentor_scope_grant' to link to 'mentor_application'.")
    else:
        print("[alter-1.63] Column 'mentor_id' not found in 'mentor_scope_grant'. Assuming already migrated. Skipping.")

    # 7. Drop the old table
    if table_exists('user_mentor_old'):
        execute("DROP TABLE `user_mentor_old`;")
        print("[alter-1.63] Dropped old 'user_mentor_old' table.")
    else:
        print("[alter-1.63] Table 'user_mentor_old' not found. Skipping drop.")


if __name__ == '__main__':
    migrate_mentor_tables()
    execute("UPDATE system_setting SET value = '1.63', updated_at = now() WHERE `key` = 'db.version';")
    print("[alter-1.63] Updated database version to 1.63.")