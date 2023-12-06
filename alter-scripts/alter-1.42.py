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
from collections import defaultdict


# 'e36958d9-79c7-47a7-9eef-dee286e1ec3f', '1', '0086b865-75b2-4207-8e1a-7345f4e98c31', '508a4b42-f579-49b6-9bd7-c3ce2a4575ac', '2023-04-25 10:32:22', '508a4b42-f579-49b6-9bd7-c3ce2a4575ac', '2023-04-25 10:32:22'

def clg_levels_check():
    results = execute("""
            SELECT
            org.id AS org_id,
            uol.user_id AS user_id,
            lvl.level_order AS lvl_order,
            w.karma_last_updated_at AS karma_last_updated_at
        FROM
            user_organization_link AS uol
        INNER JOIN
            user_lvl_link AS ull ON uol.user_id = ull.user_id
        INNER JOIN level AS lvl ON ull.level_id = lvl.id
        INNER JOIN
            wallet AS w ON w.user_id = uol.user_id
        INNER JOIN
            organization AS org ON uol.org_id = org.id
        WHERE
            org.org_type = 'College'
            AND w.karma_last_updated_at > DATE_SUB(NOW(), INTERVAL 6 MONTH)
            AND org.id IN (
                SELECT org.id FROM organization AS org
                INNER JOIN user_organization_link url ON url.org_id = org.id 
                INNER JOIN wallet AS w ON w.user_id = url.user_id
                WHERE w.karma_last_updated_at > DATE_SUB(NOW(), INTERVAL 6 MONTH)
                GROUP BY org.id 
                HAVING COUNT(*) >= 20
            )
            ORDER BY lvl_order ASC
                    """)

    data = defaultdict(lambda: defaultdict(list))

    for result in results:
        org_id, user_id, lvl_order = result[0], result[1], result[2]

        for other_lvl_order in range(1, lvl_order + 1):
            data[org_id][other_lvl_order].append(user_id)

    clg_data = {}
    for org_id, levels in data.items():
        for lvl in range(1, 8):
            if len(levels.get(lvl, [])) >= 20:
                clg_data[org_id] = lvl
            else:
                break
        print(f"Org ID: {org_id}, College Level: {lvl}")

    return clg_data


def delete_colleges():
    return execute("""DELETE FROM college""")


def insert_colleges(clgdata):
    user_id = config("SYSADMIN_ID")
    for org_id, lvl in clgdata.items():
        execute(f"""
            INSERT INTO college (id, level, org_id, updated_by, updated_at, created_by, created_at)
            VALUES ('{uuid.uuid4()}', '{lvl}', '{org_id}', '{user_id}', NOW(), '{user_id}', NOW())
            """)
    return


if __name__ == "__main__":
    data = clg_levels_check()
    delete_colleges()
    insert_colleges(data)
    execute("UPDATE system_setting SET value = '1.42', updated_at = now() WHERE `key` = 'db.version';")
