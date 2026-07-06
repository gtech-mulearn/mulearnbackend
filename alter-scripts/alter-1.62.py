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


def table_exists(table_name: str) -> bool:
    query = f"""
        SELECT COUNT(*)
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = '{DB_NAME}'
          AND TABLE_NAME = '{table_name}';
    """
    result = execute(query)
    return result and result[0][0] > 0


def create_comic_comment_table():
    if not table_exists('comic_comment'):
        execute(
            """
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
              KEY `idx_comic_comment_comic` (`comic_id`,`created_at`),
              KEY `idx_comic_comment_chapter` (`chapter_id`,`created_at`),
              KEY `idx_comic_comment_parent` (`parent_id`),
              KEY `idx_comic_comment_user` (`user_id`),
              CONSTRAINT `fk_comic_comment_ref_comic_id` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
              CONSTRAINT `fk_comic_comment_ref_parent_id` FOREIGN KEY (`parent_id`) REFERENCES `comic_comment` (`id`) ON DELETE CASCADE,
              CONSTRAINT `fk_comic_comment_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
              CONSTRAINT `fk_comic_comment_ref_del_by` FOREIGN KEY (`deleted_by`) REFERENCES `user` (`id`) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """
        )
        print("[alter-1.62] Created table 'comic_comment'.")
    else:
        print("[alter-1.62] Table 'comic_comment' already exists.")


if __name__ == '__main__':
    create_comic_comment_table()
    execute("UPDATE system_setting SET value = '1.62', updated_at = now() WHERE `key` = 'db.version';")
    print("[alter-1.62] Updated database version to 1.62.")
