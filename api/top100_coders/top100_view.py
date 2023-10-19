from django.db import connection
from rest_framework.views import APIView

from utils.response import CustomResponse


class Leaderboard(APIView):
    def get(self, request):
        # query = """
        #     SELECT u.first_name, u.last_name, SUM(kal.karma) AS total_karma, org.title as org, org.dis, org.state, u.profile_pic, MAX(kal.created_at) as time_
        #     FROM karma_activity_log AS kal
        #     INNER JOIN user AS u ON kal.user_id = u.id
        #     INNER JOIN task_list AS tl ON tl.id = kal.task_id
        #     LEFT JOIN (
        #         SELECT uol.user_id, org.id, org.title as title, d.name dis, s.name state
        #         FROM user_organization_link AS uol
        #         INNER JOIN organization AS org ON org.id = uol.org_id
        #         LEFT JOIN district AS d ON d.id = org.district_id
        #         LEFT JOIN zone AS z ON z.id = d.zone_id
        #         LEFT JOIN state AS s ON s.id = z.state_id
        #         GROUP BY uol.user_id
        #     ) as org on org.user_id = u.id
        #     WHERE tl.event = 'TOP100' AND kal.appraiser_approved = TRUE
        #     GROUP BY u.id
        #     ORDER BY total_karma DESC, time_
        #     LIMIT 100;
        # """
        query = """
        SELECT
        t.user_id,
        u.first_name,
        u.last_name,
        SUM(kal.karma) AS today_total_karma,
        y.yesterday_total_karma,
        ((t.today_total_karma - y.yesterday_total_karma) / y.yesterday_total_karma) * 100 AS percentage_difference,
        org.title AS org,
        org.dis,
        org.state,
        u.profile_pic,
        MAX(kal.created_at) AS time_
    FROM (
        SELECT
            u.id AS user_id,
            SUM(kal.karma) AS today_total_karma
        FROM karma_activity_log AS kal
        INNER JOIN user AS u ON kal.user_id = u.id
        INNER JOIN task_list AS tl ON tl.id = kal.task_id
        WHERE tl.event = 'TOP100'
          AND kal.appraiser_approved = TRUE
          AND DATE(kal.created_at) = CURDATE()
        GROUP BY u.id
    ) AS t
    JOIN (
        SELECT
            u.id AS user_id,
            SUM(kal.karma) AS yesterday_total_karma
        FROM karma_activity_log AS kal
        INNER JOIN user AS u ON kal.user_id = u.id
        INNER JOIN task_list AS tl ON tl.id = kal.task_id
        WHERE tl.event = 'TOP100'
          AND kal.approved = TRUE
          AND DATE(kal.created_at) = CURDATE() - INTERVAL 1 DAY
        GROUP BY u.id
    ) AS y ON t.user_id = y.user_id
    LEFT JOIN user_organization_link AS uol ON uol.user_id = u.id
    LEFT JOIN organization AS org ON org.id = uol.org_id
    LEFT JOIN district AS d ON d.id = org.district_id
    LEFT JOIN zone AS z ON z.id = d.zone_id
    LEFT JOIN state AS s ON s.id = z.state_id
    ORDER BY percentage_difference DESC
    LIMIT 100;
        
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]

            list_of_dicts = [dict(zip(column_names, row)) for row in results]
            return CustomResponse(response=list_of_dicts).get_success_response()
