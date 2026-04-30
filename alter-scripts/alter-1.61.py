import os
import sys
import django

from connection import execute

os.chdir("..")
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mulearnbackend.settings")
django.setup()

def migrate_to_new_ig():
    execute(
        """
ALTER TABLE interest_group
    ADD COLUMN foundation_deck_link VARCHAR(255) DEFAULT NULL;
"""
    )

if __name__ == "__main__":
    migrate_to_new_ig()
    execute(
        "UPDATE system_setting SET value = '1.61', updated_at = now() WHERE `key` = 'db.version';"
    )
