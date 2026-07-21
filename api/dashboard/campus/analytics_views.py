from rest_framework.views import APIView
from rest_framework import status
from utils.response import CustomResponse
from utils.permission import CustomizePermission
from utils.types import RoleType
from .dash_campus_helper import get_campus_context, campus_staff_required
from db.task import KarmaActivityLog
from django.db.models.functions import TruncDate
from django.db.models import Sum
from datetime import timedelta
from utils.utils import DateTimeUtils
from django.utils import timezone
from db.organization import UserOrganizationLink
from api.dashboard.learningcircle import services as lc_services
from django.core.cache import cache
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s

class CampusKarmaTrendAPI(APIView):
    authentication_classes = [CustomizePermission]
    
    @campus_staff_required
    @extend_schema(tags=['Dashboard - Campus'], description="Retrieve Campus Karma Trend.",
        responses={200: inline_serializer(
            name="CampusKarmaTrendResponse",
            fields={
                "hasError": s.BooleanField(),
                "statusCode": s.IntegerField(),
                "message": s.DictField(),
                "response": inline_serializer(
                    name="CampusKarmaTrendItem",
                    fields={
                        "date": s.CharField(allow_null=True),
                        "total_karma": s.IntegerField(),
                    },
                    many=True,
                ),
            },
        )},
    )
    def get(self, request):
        org, error = get_campus_context(request)
        if error: return error
        
        try:
            days = int(request.query_params.get('days', 7))
            days = min(max(days, 1), 365)
        except ValueError:
            days = 7
        cache_key = f"campus_karma_trend_{org.id}_{days}d"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return CustomResponse(response=cached_data).get_success_response()
            
        start_date = DateTimeUtils.get_current_utc_time() - timedelta(days=days)
        
        qs = KarmaActivityLog.objects.filter(
            user__user_organization_link_user__org=org,
            created_at__gte=start_date,
            appraiser_approved=True,
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total_karma=Sum('karma')
        ).order_by('date')
        
        data = [
            {
                "date": item["date"].isoformat() if item["date"] else None,
                "total_karma": item["total_karma"]
            }
            for item in qs
        ]
        
        cache.set(cache_key, data, 60 * 15) # Cache for 15 minutes
        
        return CustomResponse(response=data).get_success_response()

class CampusGrowthAPI(APIView):
    authentication_classes = [CustomizePermission]
    
    @campus_staff_required
    @extend_schema(tags=['Dashboard - Campus'], description="Retrieve Campus Growth.",
        responses={200: inline_serializer(
            name="CampusGrowthResponse",
            fields={
                "hasError": s.BooleanField(),
                "statusCode": s.IntegerField(),
                "message": s.DictField(),
                "response": inline_serializer(
                    name="CampusGrowthItem",
                    fields={
                        "key": s.CharField(),
                        "label": s.CharField(),
                        "value": s.IntegerField(),
                        "delta": s.IntegerField(),
                        "delta_type": s.CharField(),
                        "period": s.CharField(),
                    },
                    many=True,
                ),
            },
        )},
    )
    def get(self, request):
        org, error = get_campus_context(request)
        if error: return error
        
        cache_key = f"campus_growth_{org.id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return CustomResponse(response=cached_data).get_success_response()
        
        # True rolling 30-day windows so the "period: 30d" label is accurate
        # regardless of what day of the month it is (a calendar-month-to-date
        # window would under-report early in the month).
        now = timezone.now()
        current_window_start = now - timedelta(days=30)
        previous_window_start = now - timedelta(days=60)

        current_members = UserOrganizationLink.objects.filter(
            org=org, is_alumni=False, created_at__gte=current_window_start
        ).count()
        prev_members = UserOrganizationLink.objects.filter(
            org=org, is_alumni=False,
            created_at__gte=previous_window_start, created_at__lt=current_window_start,
        ).count()

        current_lcs = lc_services.get_campus_learning_circles(org.id).filter(created_at__gte=current_window_start).count()
        prev_lcs = lc_services.get_campus_learning_circles(org.id).filter(
            created_at__gte=previous_window_start, created_at__lt=current_window_start
        ).count()
        
        data = [
            {
                "key": "members",
                "label": "Members joined",
                "value": current_members,
                "delta": current_members - prev_members,
                "delta_type": "increase" if current_members >= prev_members else "decrease",
                "period": "30d"
            },
            {
                "key": "learning_circles",
                "label": "Learning Circles formed",
                "value": current_lcs,
                "delta": current_lcs - prev_lcs,
                "delta_type": "increase" if current_lcs >= prev_lcs else "decrease",
                "period": "30d"
            }
        ]
        
        cache.set(cache_key, data, 60 * 15) # Cache for 15 minutes
        
        return CustomResponse(response=data).get_success_response()
