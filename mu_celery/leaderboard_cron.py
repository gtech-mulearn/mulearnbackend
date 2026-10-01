import json
import datetime
from celery import shared_task
from django.core.cache import cache
from django.db.models import Exists, OuterRef, Prefetch, Sum, Q
from django.db.models.functions import Coalesce
from django.db.models import Value
from db.user import User, UserRoleLink
from db.organization import Organization, UserOrganizationLink
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils

STUDENTS_ALL_KEY = "leaderboard:students:all"
TTL = 60 * 60 * 13  # 13 hours


def _build_students_leaderboard():
    """Runs the DB query and returns a plain list of dicts."""
    is_student = UserRoleLink.objects.filter(
        user_id=OuterRef("pk"),
        role__title=RoleType.STUDENT.value,
    )
    in_college = UserOrganizationLink.objects.filter(
        user_id=OuterRef("pk"),
        org__org_type=OrganizationType.COLLEGE.value,
    )

    students = (
        User.objects
        .filter(exist_in_guild=True)
        .filter(Exists(is_student), Exists(in_college))
        .select_related("wallet_user")
        .only("id", "muid", "full_name", "wallet_user__karma")
        .prefetch_related(
            Prefetch(
                "user_organization_link_user",
                queryset=UserOrganizationLink.objects
                    .filter(org__org_type=OrganizationType.COLLEGE.value)
                    .select_related("org")
                    .only("user_id", "org__title"),
                to_attr="colleges",
            )
        )
        .order_by("-wallet_user__karma")[:20]
    )

    return [
        {
            "muid": u.muid,
            "full_name": u.full_name,
            "total_karma": u.wallet_user.karma if u.wallet_user else 0,
            "institution": u.colleges[0].org.title if u.colleges else None,
            "profile_pic": str(u.profile_pic) if u.profile_pic else None,
        }
        for u in students
    ]


def _build_students_monthly_leaderboard():
    """Build the monthly student board and return a plain list of dicts.

    profile_pic is resolved here (once per cron run) so the view never
    touches the filesystem at request time.
    """
    start, next_month = DateTimeUtils.get_current_month_range()

    is_student = UserRoleLink.objects.filter(
        user_id=OuterRef("pk"),
        role__title=RoleType.STUDENT.value,
    )
    in_college = UserOrganizationLink.objects.filter(
        user_id=OuterRef("pk"),
        org__org_type=OrganizationType.COLLEGE.value,
    )

    students = (
        User.objects
        .filter(exist_in_guild=True)
        .filter(Exists(is_student), Exists(in_college))
        .only("id", "muid", "full_name")
        .prefetch_related(
            Prefetch(
                "user_organization_link_user",
                queryset=UserOrganizationLink.objects
                    .filter(org__org_type=OrganizationType.COLLEGE.value)
                    .select_related("org")
                    .only("user_id", "org__title"),
                to_attr="colleges",
            )
        )
        .annotate(
            total_karma=Coalesce(
                Sum(
                    "karma_activity_log_user__karma",
                    filter=Q(
                        karma_activity_log_user__created_at__gte=start,
                        karma_activity_log_user__created_at__lt=next_month,
                    ),
                ),
                Value(0),
            )
        )
        .order_by("-total_karma")[:20]
    )

    return [
        {
            "muid": u.muid,
            "full_name": u.full_name,
            "total_karma": u.total_karma,
            "institution": u.colleges[0].org.title if u.colleges else None,
            "profile_pic": str(u.profile_pic) if u.profile_pic else None,
        }
        for u in students
    ]


@shared_task
def refresh_leaderboards():
    # Board 1 — students all-time
    data = _build_students_leaderboard()
    cache.set(STUDENTS_ALL_KEY, json.dumps(data), timeout=TTL)
    print(f"[leaderboard_cron] students:all pushed — {len(data)} rows")

    # Board 2 — students monthly
    month_label = datetime.datetime.utcnow().strftime("%Y-%m")
    monthly_key = f"leaderboard:students:month:{month_label}"
    monthly_data = _build_students_monthly_leaderboard()
    cache.set(monthly_key, json.dumps(monthly_data), timeout=TTL)
    print(f"[leaderboard_cron] students:month:{month_label} pushed — {len(monthly_data)} rows")

    # Board 3 — college monthly
    college_monthly_key = f"leaderboard:college:month:{month_label}"
    college_monthly_data = _build_college_monthly_leaderboard()
    cache.set(college_monthly_key, json.dumps(college_monthly_data), timeout=TTL)
    print(f"[leaderboard_cron] college:month:{month_label} pushed — {len(college_monthly_data)} rows")


def _build_college_monthly_leaderboard():
    """Build the monthly college board and return a plain list of dicts."""
    from django.db.models import Sum, Q, Count, F
    from django.db.models.functions import Coalesce
    from django.db.models import Value
    from db.organization import Organization
    from utils.types import OrganizationType

    start, next_month = DateTimeUtils.get_current_month_range()

    colleges = (
        Organization.objects.filter(
            org_type=OrganizationType.COLLEGE.value,
            user_organization_link_org__user__karma_activity_log_user__created_at__gte=start,
            user_organization_link_org__user__karma_activity_log_user__created_at__lt=next_month,
            user_organization_link_org__user__karma_activity_log_user__appraiser_approved=True,
        )
        .annotate(
            total_karma=Coalesce(
                Sum(
                    "user_organization_link_org__user__karma_activity_log_user__karma",
                    filter=Q(
                        user_organization_link_org__user__karma_activity_log_user__created_at__gte=start,
                        user_organization_link_org__user__karma_activity_log_user__created_at__lt=next_month,
                    ),
                ),
                Value(0),
            ),
            students=Count("user_organization_link_org__user", distinct=True),
        )
        .values("id", "code", "title", "total_karma", "students")
        .order_by("-total_karma")[:20]
    )

    return list(colleges)


