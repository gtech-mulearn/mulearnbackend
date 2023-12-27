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

#order of socials table must be same as socials list
socials = [
        "github",
        "facebook",
        "instagram",
        "linkedin",
        "dribble",
        "behance",
        "stackoverflow",
        "medium",
        "hackerrank"
]

def get_task_list(hashtag: str): 
    task_id = execute(f"""
        SELECT id
        FROM task_list
        WHERE hashtag = '{hashtag}';
    """)    
    return task_id[0][0] if task_id else None

def create_social_task():
    user_id = config("SYSTEM_ADMIN_ID")
    for ele in socials:
        social = f"social_{ele}"

        if get_task_list(f"#social_{ele}"):
            continue

        id = uuid.uuid4()
        task_type = execute(f"""
            SELECT id
            FROM task_type
            WHERE title = 'Mentor';
            """)
        execute(f"""
                INSERT INTO task_list (id, hashtag, title, karma, type_id, updated_by, updated_at, created_by, created_at)
                VALUES ('{id}', '#{social}', '{social}', 20, '{task_type[0][0]}', '{user_id}', now(), '{user_id}', now());
            """)
    
def alter_task_message_id():
    execute("""
        ALTER TABLE karma_activity_log MODIFY COLUMN task_message_id VARCHAR(36)
    """)

def give_karma(user_id, task_id):
     id = uuid.uuid4()

     log_id = execute(f"""
        SELECT id 
        FROM karma_activity_log
        WHERE user_id = '{user_id}' AND task_id = '{task_id}';
     """)

     if not log_id:
        execute(f"""
            INSERT INTO karma_activity_log (id, task_id, karma, user_id, updated_by, created_by, peer_approved, peer_approved_by, appraiser_approved_by, appraiser_approved, task_message_id, updated_at, created_at)
            VALUES ('{id}', '{task_id}', 20, '{user_id}', '{user_id}', '{user_id}', true, '{user_id}', '{user_id}', true, null, now(), now());
        """)
        execute(f"""
            UPDATE wallet SET karma = karma + 20 WHERE user_id = '{user_id}';
        """)

def automate_socials_karma():
    results = execute(f"""
        SELECT
            u.id, github, facebook, instagram, linkedin, dribble, behance, stackoverflow, medium, hackerrank
        FROM 
            user AS u
        INNER JOIN
            socials AS s ON s.user_id = u.id;
        """
    )

    for result in results:
        for idx, data in enumerate(result[1:]):
            social = f"#social_{socials[idx]}"
            if data and data != "":
                if result[0] == '3a77f992-a8c9-4ca3-8e00-8f1eaaf91d0c':
                    print(socials[idx])
                task_id = get_task_list(social)      
                give_karma(result[0], task_id)

if __name__ == '__main__':
    alter_task_message_id()
    create_social_task()
    automate_socials_karma()
    execute("UPDATE system_setting SET value = '1.43', updated_at = now() WHERE `key` = 'db.version';")

