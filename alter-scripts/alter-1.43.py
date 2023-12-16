import os
import sys
import uuid

import django

from connection import execute

os.chdir('..')
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mulearnbackend.settings')
django.setup()

def alter_task_message_id():
    execute("""
        ALTER TABLE karma_activity_log MODIFY COLUMN task_message_id VARCHAR(36)
    """)

def give_karma(user_id, task_id):
     id = uuid.uuid4()
     execute(f"""
        INSERT INTO karma_activity_log (id, task_id, karma, user_id, updated_by, created_by, peer_approved, peer_approved_by, appraiser_approved_by, appraiser_approved, task_message_id, updated_at, created_at)
        VALUES ('{id}', '{task_id}', 20, '{user_id}', '{user_id}', '{user_id}', true, '{user_id}', '{user_id}', true, null, now(), now());""")

     execute(f"""UPDATE wallet
        SET karma = karma + 20,
            updated_by = '{user_id}'
        WHERE user_id = '{user_id}';
        """)
    
def automate_socials_karma():
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

    results = execute(f"""
        SELECT
            u.id, github, facebook, instagram, linkedin, dribble, behance, stackoverflow, medium, hackerrank
        FROM 
            user AS u
        LEFT JOIN 
            karma_activity_log AS kal ON kal.user_id = u.id
        INNER JOIN
            socials AS s ON s.user_id = u.id
        WHERE 
            kal.user_id IS NULL OR kal.task_id NOT IN (SELECT id FROM task_list WHERE title LIKE 'social%');
        """
    )

    for result in results:
        for data in result[1:]:
            if data:
                social = f"social_{socials[result.index(data) - 1]}"
                task_id = execute(f"""
                    SELECT id 
                    FROM task_list
                    WHERE title = '{social}';
                    """)
                if task_id:
                    give_karma(result[0], task_id[0][0])

if __name__ == '__main__':
    alter_task_message_id()
    automate_socials_karma()
    execute("UPDATE system_setting SET value = '1.43', updated_at = now() WHERE `key` = 'db.version';")

