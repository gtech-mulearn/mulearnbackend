import os
import sys

import django

from connection import execute

os.chdir("..")
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mulearnbackend.settings")
django.setup()


def create_campus_execom_table():
    execute(
        """
        CREATE TABLE IF NOT EXISTS campus_execom (
            id VARCHAR(36) PRIMARY KEY NOT NULL,
            campus_id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36) NOT NULL,
            role_id VARCHAR(36) NOT NULL,
            created_by VARCHAR(36) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR(36) NOT NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY campus_execom_unique_role_per_campus (campus_id, role_id),
            KEY fk_campus_execom_ref_user (user_id),
            KEY fk_campus_execom_ref_role (role_id),
            KEY fk_campus_execom_ref_created_by (created_by),
            KEY fk_campus_execom_ref_updated_by (updated_by),
            CONSTRAINT fk_campus_execom_ref_campus FOREIGN KEY (campus_id) REFERENCES organization (id) ON DELETE CASCADE,
            CONSTRAINT fk_campus_execom_ref_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
            CONSTRAINT fk_campus_execom_ref_role FOREIGN KEY (role_id) REFERENCES role (id) ON DELETE CASCADE,
            CONSTRAINT fk_campus_execom_ref_created_by FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE CASCADE,
            CONSTRAINT fk_campus_execom_ref_updated_by FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE CASCADE
        )
        """
    )


if __name__ == "__main__":
    create_campus_execom_table()
    execute(
        "UPDATE system_setting SET value = '1.60', updated_at = now() WHERE `key` = 'db.version';"
    )
