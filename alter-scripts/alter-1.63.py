import os
import sys
from pathlib import Path
from decouple import config
import django

from connection import execute
from django.db import connection as django_connection

BASE_DIR = Path(__file__).resolve().parent.parent
os.chdir(BASE_DIR)
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mulearnbackend.settings')
django.setup()

DB_NAME = config('DATABASE_NAME')


def table_exists(table_name: str) -> bool:
    with django_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = %s;
            """,
            [DB_NAME, table_name]
        )
        row = cursor.fetchone()
    return row and row[0] > 0


def create_chapter_tables():
    if not table_exists('chapter'):
        execute(
            """
            CREATE TABLE `chapter` (
              `id` varchar(36) NOT NULL,
              `comic_id` varchar(36) NOT NULL,
              `title` varchar(150) NOT NULL,
              `slug` varchar(75) NOT NULL,
              `description` text DEFAULT NULL,
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
              CONSTRAINT `fk_chapter_ref_comic_id` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
              CONSTRAINT `fk_chapter_ref_del_by` FOREIGN KEY (`deleted_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
              CONSTRAINT `fk_chapter_ref_upd_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
              CONSTRAINT `fk_chapter_ref_cre_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """
        )
        print("[alter-1.63] Created table 'chapter'.")
    else:
        print("[alter-1.63] Table 'chapter' already exists.")

    if not table_exists('chapter_page'):
        execute(
            """
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
              CONSTRAINT `fk_chapter_page_ref_chapter_id` FOREIGN KEY (`chapter_id`) REFERENCES `chapter` (`id`) ON DELETE CASCADE,
              CONSTRAINT `fk_chapter_page_ref_del_by` FOREIGN KEY (`deleted_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
              CONSTRAINT `fk_chapter_page_ref_upd_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
              CONSTRAINT `fk_chapter_page_ref_cre_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """
        )
        print("[alter-1.63] Created table 'chapter_page'.")
    else:
        print("[alter-1.63] Table 'chapter_page' already exists.")


if __name__ == '__main__':
    create_chapter_tables()
    execute("UPDATE system_setting SET value = '1.63', updated_at = now() WHERE `key` = 'db.version';")
    print("[alter-1.63] Updated database version to 1.63.")
