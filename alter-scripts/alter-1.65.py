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


def create_task_acceptance_table():
    """
    Creates table task_acceptance to track learner problem statement / task acceptances.
    """
    query = """
        CREATE TABLE IF NOT EXISTS `task_acceptance` (
          `id` varchar(36) NOT NULL,
          `user_id` varchar(36) NOT NULL,
          `task_id` varchar(36) NOT NULL,
          `status` varchar(20) NOT NULL DEFAULT 'ACCEPTED',
          `accepted_at` datetime NOT NULL,
          `created_at` datetime NOT NULL,
          `updated_at` datetime NOT NULL,
          PRIMARY KEY (`id`),
          UNIQUE KEY `uq_task_acceptance_user_task` (`user_id`, `task_id`),
          KEY `fk_task_acceptance_ref_user_id` (`user_id`),
          KEY `fk_task_acceptance_ref_task_id` (`task_id`),
          CONSTRAINT `fk_task_acceptance_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
          CONSTRAINT `fk_task_acceptance_ref_task_id` FOREIGN KEY (`task_id`) REFERENCES `task_list` (`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
    """
    execute(query)
    print("[alter-1.65] Created table 'task_acceptance' if not existing.")


if __name__ == '__main__':
    create_task_acceptance_table()
    execute("UPDATE system_setting SET value = '1.65', updated_at = now() WHERE `key` = 'db.version';")
    print("[alter-1.65] Updated database version to 1.65.")
