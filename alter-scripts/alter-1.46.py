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

from utils.utils import DiscordWebhooks
from utils.types import WebHookActions, WebHookCategory

def is_role_exist(title) -> bool:
    query = f"""SELECT id FROM role WHERE title = '{title}'"""
    return execute(query)

def get_intrest_groups():
    query = f"""SELECT name,code, created_by FROM interest_group"""
    return execute(query)

def create_ig_lead_roles():
    for name,code,created_by in get_intrest_groups():
        role_name = code+' CampusLead'
        if is_role_exist(role_name) is not None:
            query = f"""INSERT INTO role (id, title, description ,created_by, updated_by,updated_at,created_at)
                        VALUES (
                            '{uuid.uuid4()}',
                            '{role_name}',
                            '{f'Campus Lead of {name} Interest Group'}',
                            '{created_by}',
                            '{created_by}',
                            UTC_TIMESTAMP,
                            UTC_TIMESTAMP
                        )
                """
            execute(query)
            DiscordWebhooks.general_updates(
                WebHookCategory.ROLE.value,
                WebHookActions.CREATE.value,
                role_name
            )

if __name__ == '__main__':
    create_ig_lead_roles()
    execute("UPDATE system_setting SET value = '1.46', updated_at = now() WHERE `key` = 'db.version';")

