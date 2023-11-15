from django.db import connection
from rest_framework.views import APIView

from utils.response import CustomResponse


class Leaderboard(APIView):
    def get(self, request):
        query = """
                SELECT 
                u.id,
                u.first_name, 
                u.last_name, 
                SUM(kal.karma) AS karma,
                COALESCE(org.title, comm.title) AS org,
                COALESCE(org.dis, d.name) AS district,
                COALESCE(org.state, s.name) AS state,
                MAX(kal.created_at) AS time_
                FROM karma_activity_log AS kal
                INNER JOIN user AS u ON kal.user_id = u.id
                INNER JOIN task_list AS tl ON tl.id = kal.task_id
                LEFT JOIN (
                    SELECT 
                        uol.user_id, 
                        org.id, 
                        org.title AS title, 
                        d.name dis, 
                        s.name state
                    FROM user_organization_link AS uol
                    INNER JOIN organization AS org ON org.id = uol.org_id AND org.org_type IN ('College', 'School', 'Company')
                    LEFT JOIN district AS d ON d.id = org.district_id
                    LEFT JOIN zone AS z ON z.id = d.zone_id
                    LEFT JOIN state AS s ON s.id = z.state_id
                    GROUP BY uol.user_id 
                    ) AS org ON org.user_id = u.id
                    LEFT JOIN (SELECT 
                        uol.user_id, 
                        org.id, 
                        org.title AS title
                    FROM user_organization_link AS uol
                    INNER JOIN organization AS org ON org.id = uol.org_id AND org.org_type IN ('Community')
                    GROUP BY uol.user_id) AS comm ON comm.user_id = u.id
                    LEFT JOIN district AS d ON d.id = u.district_id
                    LEFT JOIN zone AS z ON d.zone_id = z.id
                    LEFT JOIN state AS s ON z.state_id = s.id
                    WHERE 
                        tl.event = 'TOP100' AND
                        kal.appraiser_approved = TRUE 
                        AND u.id IN (select user_id from karma_activity_log as kal
                    INNER JOIN task_list AS tl ON tl.id = kal.task_id
                    WHERE tl.hashtag = '#thc-realworld-problem-proposal' AND kal.appraiser_approved = TRUE)
                    GROUP BY u.id
                    ORDER BY karma DESC, time_;

        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]

            list_of_dicts = [dict(zip(column_names, row)) for row in results]
            return CustomResponse(response=list_of_dicts).get_success_response()
