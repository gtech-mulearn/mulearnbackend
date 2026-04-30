import os
import sys
import django

from connection import execute

os.chdir("..")
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mulearnbackend.settings")
django.setup()


def migrate_profile_fields():
    """Add bio, projects, and experience fields to user table"""
    execute("""
ALTER TABLE user
ADD COLUMN bio LONGTEXT NULL DEFAULT NULL,
ADD COLUMN projects JSON NULL DEFAULT NULL,
ADD COLUMN experience JSON NULL DEFAULT NULL;
    """)
    print("Successfully added bio, projects, and experience fields to user table")


if __name__ == "__main__":
    try:
        migrate_profile_fields()
        execute(
            "UPDATE system_setting SET value = '2.60', updated_at = now() WHERE `key` = 'db.version';"
        )
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
