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


def column_exists(column_name: str) -> bool:
    # Guard against double-running the script on environments that already have the column
    query = f"""
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = '{DB_NAME}'
          AND TABLE_NAME = 'company_jobs'
          AND COLUMN_NAME = '{column_name}';
    """
    result = execute(query)
    return result and result[0][0] > 0


def add_total_views_column():
    if not column_exists('total_views'):
        execute(
            """
ALTER TABLE company_jobs
    ADD COLUMN total_views INT NOT NULL DEFAULT 0;
            """
        )
        print("[alter-1.61] Added column 'total_views' to 'company_jobs' table.")
    else:
        print("[alter-1.61] Column 'total_views' already exists in 'company_jobs' table.")


if __name__ == '__main__':
    add_total_views_column()
    execute("UPDATE system_setting SET value = '1.61', updated_at = now() WHERE `key` = 'db.version';")
    print("[alter-1.61] Updated database version to 1.61.")
