from django.db.models import Sum, Max, Prefetch, F, OuterRef, Subquery, IntegerField
from django.db import connection
from rest_framework.views import APIView

from .serializers import LaunchpadLeaderBoardSerializer
from utils.response import CustomResponse
from utils.utils import CommonUtils
from db.user import User
from db.organization import UserOrganizationLink
from db.task import KarmaActivityLog



class Leaderboard(APIView):
    def get(self, request):
        total_karma_subquery = KarmaActivityLog.objects.filter(
            user=OuterRef('id'),
            task__event='launchpad',
            appraiser_approved=True,
        ).values('user').annotate(
            total_karma=Sum('karma')
        ).values('total_karma')
        allowed_org_types = ["College", "School", "Company"]

        users = User.objects.filter(
            karma_activity_log_user__task__event="launchpad",
            karma_activity_log_user__appraiser_approved=True,
            id__in=intro_task_completed_users
        ).prefetch_related(
            Prefetch(
                "user_organization_link_user",
                queryset=UserOrganizationLink.objects.filter(org__org_type__in=allowed_org_types),
            )
        ).filter(
            user_organization_link_user__id__in=UserOrganizationLink.objects.filter(
                org__org_type__in=allowed_org_types
            ).values("id")
        ).annotate(
            karma=Subquery(total_karma_subquery, output_field=IntegerField()),
            org=F("user_organization_link_user__org__title"),
            district_name=F("user_organization_link_user__org__district__name"),
            state=F("user_organization_link_user__org__district__zone__state__name"),
            time_=Max("karma_activity_log_user__created_at"),
        ).order_by("-karma", "time_")

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users,
            request,
            ["full_name", "karma", "org", "district_name", "state"]
        )

        serializer = LaunchpadLeaderBoardSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )
# class Leaderboard(APIView):
#     def get(self, request):
#         total_karma_subquery = KarmaActivityLog.objects.filter(
#             user=OuterRef('id'),
#             task__event='launchpad',
#             appraiser_approved=True,
#         ).values('user').annotate(
#             total_karma=Sum('karma')
#         ).values('total_karma')


#         users = (
#             User.objects.filter(
#                 karma_activity_log_user__task__event="launchpad",
#                 karma_activity_log_user__appraiser_approved=True,
#                 karma_activity_log_user__task__hashtag="#lp24-introduction",
#             ).prefetch_related(
#                 Prefetch(
#                     "user_organization_link_user",
#                     queryset=UserOrganizationLink.objects.filter(
#                         org__org_type__in=["College", "School", "Company", "Community"]
#                     ),
#                 )
#             )
#             .annotate(
#                 karma=Subquery(total_karma_subquery, output_field=IntegerField()),
#                 org=F("user_organization_link_user__org__title"),
#                 district_name=F("user_organization_link_user__org__district__name"),
#                 state=F("user_organization_link_user__org__district__zone__state__name"),
#                 time_=Max("karma_activity_log_user__created_at"),
#             )
#         )

#         paginated_queryset = CommonUtils.get_paginated_queryset(
#            users,
#             request,
#             ["karma", "org", "district_name", "state", "time_"],
#             sort_fields={
#                 "-karma": "-karma",
#                 "time_": "time_",
#             },
#         )

#         serializer = LaunchpadLeaderBoardSerializer(
#             paginated_queryset.get("queryset"), many=True
#         )
#         return CustomResponse().paginated_response(
#             data=serializer.data, pagination=paginated_queryset.get("pagination")
#         )
# class Leaderboard(APIView):
#     def get(self, request):
#         query = """
#         SELECT 
#             u.full_name, 
#             SUM(kal.karma) AS karma,
#             COALESCE(org.title, comm.title) AS org,
#             COALESCE(org.dis, d.name) AS district,
#             COALESCE(org.state, s.name) AS state,
#             MAX(kal.created_at) AS time_
#         FROM karma_activity_log AS kal
#         INNER JOIN user AS u ON kal.user_id = u.id
#         INNER JOIN task_list AS tl ON tl.id = kal.task_id
#         LEFT JOIN (
#             SELECT 
#                 uol.user_id,
#                 org.id, 
#                 org.title AS title, 
#                 d.name dis, 
#                 s.name state
#             FROM user_organization_link AS uol
#             INNER JOIN organization AS org ON org.id = uol.org_id AND org.org_type IN 
#             ("College", "School", "Company")
#             LEFT JOIN district AS d ON d.id = org.district_id
#             LEFT JOIN zone AS z ON z.id = d.zone_id
#             LEFT JOIN state AS s ON s.id = z.state_id
#             GROUP BY uol.user_id
#         ) AS org ON org.user_id = u.id
#         LEFT JOIN (
#             SELECT 
#                 uol.user_id,
#                 org.id, 
#                 org.title AS title
#             FROM organization AS org
#             INNER JOIN user_organization_link AS uol ON org.id = uol.org_id AND org.org_type IN ("Community")
#             GROUP BY uol.user_id
#         ) AS comm ON comm.user_id = u.id
#         LEFT JOIN district AS d ON d.id = u.district_id
#         LEFT JOIN zone AS z ON d.zone_id = z.id
#         LEFT JOIN state AS s ON z.state_id = s.id
#         WHERE 
#             tl.event = "launchpad" AND
#             kal.appraiser_approved = TRUE AND
#             u.id IN (
#                 SELECT karma_activity_log.user_id FROM karma_activity_log 
#                 INNER JOIN task_list ON karma_activity_log.task_id = task_list.id
#                 WHERE
#                     task_list.hashtag = "#lp24-introduction" AND
#                     karma_activity_log.appraiser_approved = TRUE
#             )
#         GROUP BY u.id
#         ORDER BY karma DESC, time_
#         """
#         with connection.cursor() as cursor:
#             cursor.execute(query)
#             results = cursor.fetchall()
#             column_names = [desc[0] for desc in cursor.description]
#             user_ids = set()
#             list_of_dicts = []
#             for row in results:
#                 if row[0] not in user_ids:
#                     user_ids.add(row[0])
#                     list_of_dicts.append(dict(zip(column_names, row)))
#             return CustomResponse(response=list_of_dicts).get_success_response()

