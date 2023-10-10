from rest_framework.views import APIView
from db.task import KarmaActivityLog
from utils.types import Events
from django.db.models import Sum
from api.top100_coders.top100_serializer import Top100CodersSerializer
from utils.response import CustomResponse


class Leaderboard(APIView):
    def get(self, request):
        coders = (
            KarmaActivityLog.objects
            .select_related('user', 'task')
            .prefetch_related('user__user_organization_link_user__org__district__zone__state')
            .filter(task__event=Events.TOP_100_CODERS.value, user__exist_in_guild=True, user__active=True,
                    appraiser_approved=True)
            .values('user__first_name', 'user__last_name', 'user__user_organization_link_user__org__title',
                    'user__user_organization_link_user__org__district__name',
                    'user__user_organization_link_user__org__district__zone__state__name')
            .annotate(total_karma=Sum('karma'))
            .order_by('-total_karma')
            [:100]
        )
        coders = list(coders)
        for rank, coder in enumerate(coders, start=1):
            coder['rank'] = rank
        serialized_data = Top100CodersSerializer(coders, many=True).data
        return CustomResponse(response=serialized_data).get_success_response()
