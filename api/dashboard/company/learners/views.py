from rest_framework import status
from rest_framework.views import APIView

from db.company import Company
from db.user import User, UserRoleLink, UserSettings
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils

from .serializers import LearnerListSerializer


class LearnerDiscoveryAPIView(APIView):
    """
    GET company/learners/

    Returns a paginated, filterable list of learners whose profile is set to
    public (UserSettings.is_public = True).

    Authorization:
        - JWT required
        - Caller must have the 'Company' role
        - Caller must have an active Company record

    Query parameters (all optional):
        karma_min          (int)  — minimum wallet karma
        karma_max          (int)  — maximum wallet karma
        ig_ids             (str)  — comma-separated Interest Group UUIDs
        achievement_ids    (str)  — comma-separated Achievement UUIDs
        level_order_min    (int)  — minimum level_order (e.g. 3 → Level 3+)
        interested_in_work (bool) — "true" to filter opt-in learners
        interested_in_gig_work (bool) — "true" to filter gig opt-in learners

    Standard pagination / search:
        pageIndex, perPage, search, sortBy
    """

    permission_classes = [CustomizePermission]

    # ------------------------------------------------------------------ #
    # Authorization helpers                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _get_user(request):
        """Extract the authenticated User object from the JWT token."""
        try:
            user_id = JWTUtils.fetch_user_id(request)
        except Exception:
            return None
        return User.objects.filter(id=user_id).first()

    @staticmethod
    def _is_company_user(user):
        """Return True if the user holds the Company role."""
        return UserRoleLink.objects.filter(
            user=user,
            role__title=RoleType.COMPANY.value,
        ).exists()

    @staticmethod
    def _has_active_company(user):
        """Return True if the user owns at least one active Company record."""
        return Company.objects.filter(
            company_user_id=user,
            status="active",
        ).exists()

    # ------------------------------------------------------------------ #
    # Filter helpers                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_int_param(request, key):
        """
        Parse an integer query param.
        Returns (value, error_response) — one of the two will be None.
        """
        raw = request.query_params.get(key)
        if raw is None:
            return None, None
        try:
            return int(raw), None
        except ValueError:
            error = CustomResponse(
                general_message=f"Invalid value for '{key}': must be an integer.",
                message={"error_code": "INVALID_FILTER_VALUE"},
            ).get_failure_response(
                status_code=400,
                http_status_code=status.HTTP_400_BAD_REQUEST,
            )
            return None, error

    @staticmethod
    def _parse_ids_param(request, key):
        """
        Parse a comma-separated UUID list query param.
        Returns a list of stripped strings, or an empty list if absent.
        """
        raw = request.query_params.get(key)
        if not raw:
            return []
        return [v.strip() for v in raw.split(",") if v.strip()]

    @staticmethod
    def _parse_bool_param(request, key):
        """
        Parse a boolean query param ('true'/'1' → True).
        Returns True only if explicitly set to a truthy string value.
        """
        raw = request.query_params.get(key, "").lower()
        return raw in ("true", "1", "yes")

    # ------------------------------------------------------------------ #
    # Main handler                                                         #
    # ------------------------------------------------------------------ #

    def get(self, request):
        # 1. Authenticate
        user = self._get_user(request)
        if not user:
            return CustomResponse(
                general_message="User not found or token invalid.",
                message={"error_code": "USER_NOT_FOUND"},
            ).get_failure_response(
                status_code=401,
                http_status_code=status.HTTP_401_UNAUTHORIZED,
            )

        # 2. Authorise — must be a company user with an active company
        if not self._is_company_user(user):
            return CustomResponse(
                general_message="Company role required to access learner discovery.",
                message={"error_code": "COMPANY_ROLE_REQUIRED"},
            ).get_failure_response(
                status_code=403,
                http_status_code=status.HTTP_403_FORBIDDEN,
            )

        if not self._has_active_company(user):
            return CustomResponse(
                general_message="No active company profile found for this user.",
                message={"error_code": "NO_ACTIVE_COMPANY"},
            ).get_failure_response(
                status_code=403,
                http_status_code=status.HTTP_403_FORBIDDEN,
            )

        # 3. Parse & validate filter params
        karma_min, err = self._parse_int_param(request, "karma_min")
        if err:
            return err

        karma_max, err = self._parse_int_param(request, "karma_max")
        if err:
            return err

        level_order_min, err = self._parse_int_param(request, "level_order_min")
        if err:
            return err

        ig_ids = self._parse_ids_param(request, "ig_ids")
        achievement_ids = self._parse_ids_param(request, "achievement_ids")
        filter_work = self._parse_bool_param(request, "interested_in_work")
        filter_gig = self._parse_bool_param(request, "interested_in_gig_work")

        # 4. Build base queryset
        #    - Only public profiles (UserSettings.is_public = True)
        #    - Exclude suspended users
        #    - Exclude company users themselves
        queryset = (
            User.objects.filter(
                suspended_at__isnull=True,
                user_settings_user__is_public=True,
            )
            .exclude(
                # Don't surface other company users as "learners"
                user_role_link_user__role__title=RoleType.COMPANY.value
            )
            .select_related(
                "wallet_user",           # karma
                "user_lvl_link_user__level",  # level
                "district",             # district name
            )
            .prefetch_related(
                "user_ig_link_user__ig",   # interest groups
            )
            .order_by("-wallet_user__karma")
        )

        # 5. Apply optional filters
        if karma_min is not None:
            queryset = queryset.filter(wallet_user__karma__gte=karma_min)

        if karma_max is not None:
            queryset = queryset.filter(wallet_user__karma__lte=karma_max)

        if level_order_min is not None:
            queryset = queryset.filter(
                user_lvl_link_user__level__level_order__gte=level_order_min
            )

        if ig_ids:
            queryset = queryset.filter(
                user_ig_link_user__ig__id__in=ig_ids
            ).distinct()

        if achievement_ids:
            queryset = queryset.filter(
                achievements__achievement_id__id__in=achievement_ids
            ).distinct()

        if filter_work:
            queryset = queryset.filter(interested_in_work=True)

        if filter_gig:
            queryset = queryset.filter(interested_in_gig_work=True)

        # 6. Paginate (uses CommonUtils — same as jobs module)
        try:
            paginated_data = CommonUtils.get_paginated_queryset(
                queryset=queryset,
                request=request,
                search_fields=["full_name", "muid", "district__name"],
                sort_fields={
                    "karma": "wallet_user__karma",
                    "level": "user_lvl_link_user__level__level_order",
                    "name": "full_name",
                },
                is_pagination=True,
            )
        except Exception:
            return CustomResponse(
                general_message="Something went wrong while fetching learners.",
                message={"error_code": "SERVER_ERROR"},
            ).get_failure_response(
                status_code=500,
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        paginated_learners = list(paginated_data["queryset"])
        pagination_info = paginated_data["pagination"]

        # 7. Serialize
        serializer = LearnerListSerializer(paginated_learners, many=True)

        return CustomResponse(
            general_message="Learners fetched successfully.",
            response={
                "learners": serializer.data,
                "pagination": pagination_info,
            },
        ).get_success_response()
