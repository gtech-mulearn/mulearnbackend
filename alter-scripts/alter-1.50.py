import os
import sys
import uuid
from decouple import config
import django

from connection import execute

os.chdir('..')
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mulearnbackend.settings')
django.setup()

from db.launchpad import LaunchPadUsers
from utils.types import LaunchPadRoles

def create_launchpad_admin():
    query = f"SELECT id FROM launchpad_user WHERE email = '{config('LAUNCHPAD_ADMIN_EMAIL')}'"
    if execute(query):
        return
    query = f"""
            INSERT INTO launchpad_user (id, email, role, created_at, updated_at)
                VALUES (
                    '{uuid.uuid4()}',
                    '{config('LAUNCHPAD_ADMIN_EMAIL')}',
                    '{LaunchPadRoles.ADMIN.value}',
                    UTC_TIMESTAMP,
                    UTC_TIMESTAMP
                )
            """
    execute(query)

if __name__ == '__main__':
    create_launchpad_admin()
    execute("UPDATE system_setting SET value = '1.50', updated_at = now() WHERE `key` = 'db.version';")
