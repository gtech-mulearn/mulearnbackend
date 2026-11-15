import json

from decouple import config as decouple_config
from django.core.files.storage import FileSystemStorage
from django.db import connection
from rest_framework.renderers import JSONRenderer

from api.leaderboard.leaderboard_view import get_or_rebuild_leaderboard
from rest_framework.views import APIView

from utils.response import CustomResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s


class Leaderboard(APIView):
    @extend_schema(tags=['Top100 Coders'], description="Retrieve Leaderboard.",
        responses={200: inline_serializer(
            name='Top100LeaderboardItem',
            fields={
                'id': s.CharField(),
                'full_name': s.CharField(),
                'profile_pic': s.CharField(allow_null=True),
                'total_karma': s.IntegerField(allow_null=True),
                'org': s.CharField(allow_null=True),
                'dis': s.CharField(allow_null=True),
                'state': s.CharField(allow_null=True),
                'time_': s.DateTimeField(allow_null=True),
            },
            many=True,
        )},
    )
    def get(self, request):
        query = """
        SELECT 
        u.id,
        u.full_name, 
        SUM(kal.karma) AS total_karma,
        COALESCE(org.title, comm.title) AS org,
        COALESCE(org.dis, d.name) AS dis,
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
            ORDER BY total_karma DESC, time_;
            """
        def build():
            with connection.cursor() as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]

            fs = FileSystemStorage()
            domain = decouple_config("BE_DOMAIN_NAME")
            rows = []
            for row in results:
                item = dict(zip(column_names, row))
                # profile_pic is not a column (User.profile_pic is a property
                # that checks for the uploaded file), so selecting u.profile_pic
                # made this endpoint fail with "Unknown column" on every call.
                # Resolved here the same way the property does.
                path = f"user/profile/{item['id']}.png"
                pic = f"{domain}{fs.url(path)}" if fs.exists(path) else None
                rows.append({
                    "id": item["id"],
                    "full_name": item["full_name"],
                    "profile_pic": pic,
                    **{k: v for k, v in item.items() if k not in ("id", "full_name")},
                })
            return json.loads(JSONRenderer().render(rows))

        # No parameters: one fixed key. The query scans and groups all of
        # user_organization_link twice, so it runs at most once per 10 minutes.
        data = get_or_rebuild_leaderboard("top100:leaderboard", build, timeout=60 * 10)
        return CustomResponse(response=data).get_success_response()
