import os
import sys
import django

from connection import execute

os.chdir("..")
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mulearnbackend.settings")
django.setup()

def migrate():
    execute("ALTER TABLE user ADD COLUMN bio VARCHAR(255);")
    execute("ALTER TABLE user ADD COLUMN projects JSON;")
    execute("ALTER TABLE user ADD COLUMN experience JSON;")

if __name__ == "__main__":
    migrate()
    execute(
        "UPDATE system_setting SET value = '1.60', updated_at = now() WHERE `key` = 'db.version';"
    )
