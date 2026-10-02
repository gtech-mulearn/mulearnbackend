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


def create_problem_statement_tables():
    """
    Creates the Problem Statement feature tables if they do not exist:
    - problem_statement
    - problem_statement_interest
    - problem_statement_audit_log
    """
    execute("""
        CREATE TABLE IF NOT EXISTS `problem_statement` (
          `id` varchar(36) NOT NULL,
          `company_id` varchar(36) NOT NULL,
          `title` varchar(200) NOT NULL,
          `slug` varchar(220) NOT NULL,
          `summary` varchar(500) NOT NULL,
          `description` text NOT NULL,
          `categories` json DEFAULT NULL,
          `skills` json DEFAULT NULL,
          `requirements` text DEFAULT NULL,
          `expected_outcome` text DEFAULT NULL,
          `resources` json DEFAULT NULL,
          `cover_image` varchar(512) DEFAULT NULL,
          `difficulty` varchar(20) NOT NULL DEFAULT 'intermediate',
          `reward_type` varchar(50) NOT NULL DEFAULT 'none',
          `reward_details` text DEFAULT NULL,
          `contact_email` varchar(100) DEFAULT NULL,
          `external_link` varchar(500) DEFAULT NULL,
          `deadline` datetime DEFAULT NULL,
          `status` varchar(20) NOT NULL DEFAULT 'draft',
          `removal_reason` varchar(500) DEFAULT NULL,
          `is_featured` tinyint(1) NOT NULL DEFAULT '0',
          `view_count` int unsigned NOT NULL DEFAULT '0',
          `interest_count` int unsigned NOT NULL DEFAULT '0',
          `published_at` datetime DEFAULT NULL,
          `closed_at` datetime DEFAULT NULL,
          `archived_at` datetime DEFAULT NULL,
          `created_by` varchar(36) NOT NULL,
          `updated_by` varchar(36) NOT NULL,
          `created_at` datetime NOT NULL,
          `updated_at` datetime NOT NULL,
          `deleted_at` datetime DEFAULT NULL,
          `deleted_by` varchar(36) DEFAULT NULL,
          PRIMARY KEY (`id`),
          UNIQUE KEY `uq_ps_slug` (`slug`),
          KEY `idx_ps_company_id` (`company_id`),
          KEY `idx_ps_status` (`status`),
          KEY `idx_ps_deadline` (`deadline`),
          KEY `idx_ps_created_by` (`created_by`),
          KEY `idx_ps_is_featured` (`is_featured`),
          CONSTRAINT `fk_ps_ref_company_id` FOREIGN KEY (`company_id`) REFERENCES `company` (`id`) ON DELETE CASCADE,
          CONSTRAINT `fk_ps_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`),
          CONSTRAINT `fk_ps_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`),
          CONSTRAINT `fk_ps_ref_deleted_by` FOREIGN KEY (`deleted_by`) REFERENCES `user` (`id`) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
    """)
    print("[alter-1.65] Created table 'problem_statement' if not exists.")

    execute("""
        CREATE TABLE IF NOT EXISTS `problem_statement_interest` (
          `id` varchar(36) NOT NULL,
          `problem_statement_id` varchar(36) NOT NULL,
          `user_id` varchar(36) NOT NULL,
          `status` varchar(20) NOT NULL DEFAULT 'interested',
          `note` text DEFAULT NULL,
          `work_link` varchar(500) DEFAULT NULL,
          `status_updated_by` varchar(36) NOT NULL,
          `status_updated_at` datetime NOT NULL,
          `expressed_at` datetime NOT NULL,
          `created_at` datetime NOT NULL,
          `updated_at` datetime NOT NULL,
          PRIMARY KEY (`id`),
          UNIQUE KEY `uq_ps_interest_ps_user` (`problem_statement_id`, `user_id`),
          KEY `idx_psi_user_id` (`user_id`),
          KEY `idx_psi_status` (`status`),
          CONSTRAINT `fk_psi_ref_ps_id` FOREIGN KEY (`problem_statement_id`) REFERENCES `problem_statement` (`id`) ON DELETE CASCADE,
          CONSTRAINT `fk_psi_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
          CONSTRAINT `fk_psi_ref_status_upd_by` FOREIGN KEY (`status_updated_by`) REFERENCES `user` (`id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
    """)
    print("[alter-1.65] Created table 'problem_statement_interest' if not exists.")

    execute("""
        CREATE TABLE IF NOT EXISTS `problem_statement_audit_log` (
          `id` varchar(36) NOT NULL,
          `problem_statement_id` varchar(36) NOT NULL,
          `target_type` varchar(50) NOT NULL DEFAULT 'problem_statement',
          `target_id` varchar(36) NOT NULL,
          `action` varchar(50) NOT NULL,
          `actor_id` varchar(36) NOT NULL,
          `actor_role` varchar(50) DEFAULT NULL,
          `metadata` json DEFAULT NULL,
          `created_at` datetime NOT NULL,
          PRIMARY KEY (`id`),
          KEY `idx_psal_ps_id` (`problem_statement_id`),
          KEY `idx_psal_actor_id` (`actor_id`),
          KEY `idx_psal_action` (`action`),
          CONSTRAINT `fk_psal_ref_ps_id` FOREIGN KEY (`problem_statement_id`) REFERENCES `problem_statement` (`id`) ON DELETE CASCADE,
          CONSTRAINT `fk_psal_ref_actor_id` FOREIGN KEY (`actor_id`) REFERENCES `user` (`id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
    """)
    print("[alter-1.65] Created table 'problem_statement_audit_log' if not exists.")


if __name__ == '__main__':
    create_problem_statement_tables()
    execute("UPDATE system_setting SET value = '1.65', updated_at = now() WHERE `key` = 'db.version';")
    print("[alter-1.65] Updated database version to 1.65.")
