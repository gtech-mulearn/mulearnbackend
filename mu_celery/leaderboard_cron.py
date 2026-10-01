import json
from celery import shared_task
from django.core.cache import cache
from django.db.models import Exists, OuterRef, Prefetch
from db.user import User, UserRoleLink
from db.organization import Organization, UserOrganizationLink
from utils.types import OrganizationType, RoleType

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
        .only("muid", "full_name","wallet_user__karma")
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


@shared_task
def refresh_leaderboards():
    data = _build_students_leaderboard()
    cache.set(STUDENTS_ALL_KEY, json.dumps(data), timeout=TTL)
    print(f"[leaderboard_cron] students:all pushed — {len(data)} rows")
