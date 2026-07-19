from django.db.models import Count, Q, Max
from db.learning_circle import LearningCircle, UserCircleLink

def get_campus_learning_circles(org_id: str):
    """
    Returns all Learning Circles for a specific campus.
    Enforces tenant isolation by strictly filtering LearningCircle by org_id.
    """
    return LearningCircle.objects.filter(org_id=org_id).annotate(
        member_count=Count('user_circle_link_circle__user', distinct=True, filter=Q(user_circle_link_circle__accepted=True)),
        meeting_count=Count('circle_meeting_log_circle_id'),
        last_meeting_time=Max('circle_meeting_log_circle_id__meet_time')
    )

def get_top_learning_circles(org_id: str):
    return get_campus_learning_circles(org_id).order_by('-member_count')

def get_lc_members(circle_id: str, org_id: str):
    return UserCircleLink.objects.filter(
        circle_id=circle_id,
        circle__org_id=org_id,
        accepted=True
    ).select_related('user', 'user__wallet_user', 'user__user_lvl_link_user__level')
