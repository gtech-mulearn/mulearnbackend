from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from rest_framework.views import APIView

from db.user import User
from utils.response import CustomResponse
from .dash_user_serializer import UserDashboardSerializer


class UserAPI(APIView):
    FIELDS = [
        "id",
        "discord_id",
        "mu_id",
        "first_name",
        "last_name",
        "email",
        "mobile",
        "gender",
        "dob",
        "admin",
        "active",
        "exist_in_guild",
        "created_at",
        "total_karma",
    ]

    def get(self, request):
        query_params = request.GET
        queryset = self.filter_users(query_params)
        paginated_queryset = self.paginate_users(queryset, request)
        serializer = UserDashboardSerializer(paginated_queryset, many=True)
        serialized_data = serializer.data

        return CustomResponse(
            response={"users": serialized_data}
        ).get_success_response()

    def filter_users(self, query_params):
        query_filters = Q()
        filtered_params = {
            key: value
            for key, value in query_params.items()
            if key in self.FIELDS and value
        }

        for key, value in filtered_params.items():
            query_filters &= Q(**{f"{key}__icontains": value})

        return User.objects.filter(query_filters)

    def paginate_users(self, queryset, request):
        per_page = 3
        paginator = Paginator(queryset, per_page)

        page = request.GET.get("page", 1)

        try:
            paginated_users = paginator.page(page)
        except PageNotAnInteger:
            paginated_users = paginator.page(1)
        except EmptyPage:
            paginated_users = paginator.page(paginator.num_pages)

        return paginated_users
