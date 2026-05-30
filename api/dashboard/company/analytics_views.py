from rest_framework.views import APIView
from django.db.models import Avg, Count
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from db.job import CompanyJob, UserJobApplication
from db.company import Company
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

class CompanyGigAnalyticsAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Analytics'],
        description="Retrieve analytics data for company gigs.",
        responses={
            200: inline_serializer(
                name='CompanyGigAnalyticsResponse',
                fields={
                    'total_gigs_posted': serializers.IntegerField(),
                    'active_gigs': serializers.IntegerField(),
                    'closed_gigs': serializers.IntegerField(),
                    'average_hourly_rate': serializers.FloatField(),
                    'application_funnel': serializers.DictField(),
                    'conversion_rate': serializers.CharField(),
                }
            )
        }
    )
    @role_required([RoleType.COMPANY.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id).first()
        
        if not company:
            return CustomResponse(general_message="Company profile not found.").get_failure_response(status_code=404)

        gigs = CompanyJob.objects.filter(company=company, job_type='Gig', is_deleted=False)
        
        total_gigs_posted = gigs.count()
        active_gigs = gigs.filter(status='Active').count()
        closed_gigs = gigs.filter(status='Closed').count()
        
        avg_hourly_rate = gigs.aggregate(Avg('hourly_rate'))['hourly_rate__avg'] or 0.0

        applications = UserJobApplication.objects.filter(job__in=gigs)
        total_applications = applications.count()
        
        funnel_data = applications.values('status').annotate(count=Count('status'))
        funnel_dict = {
            "Total": total_applications,
            "Pending": 0,
            "In-Review": 0,
            "Shortlisted": 0,
            "Interview": 0,
            "Selected": 0,
            "Rejected": 0
        }
        
        for item in funnel_data:
            funnel_dict[item['status']] = item['count']
            
        selected_count = funnel_dict["Selected"]
        conversion_rate = f"{(selected_count / total_applications * 100):.2f}%" if total_applications > 0 else "0.00%"
        
        response_data = {
            "total_gigs_posted": total_gigs_posted,
            "active_gigs": active_gigs,
            "closed_gigs": closed_gigs,
            "average_hourly_rate": float(f"{avg_hourly_rate:.2f}"),
            "application_funnel": funnel_dict,
            "conversion_rate": conversion_rate
        }
        
        return CustomResponse(response=response_data).get_success_response()
