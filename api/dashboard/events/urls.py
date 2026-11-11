from django.urls import path

from . import public_views, manage_views, admin_views, scoped_views, meta_views, task_views, analytics_views

urlpatterns = [

    # ── Meta (BEFORE wildcards) ───────────────────────────────
    path('meta/categories/', meta_views.EventCategoriesAPI.as_view()),
    path('meta/organizer-options/', meta_views.OrganizerOptionsAPI.as_view()),
    path('meta/collaboration-targets/', meta_views.CollaborationTargetsAPI.as_view()),
    path('meta/event-type-scope/', meta_views.EventTypesScopesAPI.as_view()),
    path('meta/linkable-events/', meta_views.LinkableEventsAPI.as_view()),

    # ── Scoped Feeds ──────────────────────────────────────────
    # cluster must come BEFORE ig/<ig_id>/ to avoid being swallowed by wildcard
    path('ig/cluster/<str:cluster>/', scoped_views.ClusterEventListAPI.as_view()),
    path('ig/<str:ig_id>/', scoped_views.IGEventListAPI.as_view()),
    path('campus/<str:campus_id>/', scoped_views.CampusEventListAPI.as_view()),
    path('campus-ig/<str:campus_ig_id>/', scoped_views.CampusIGEventListAPI.as_view()),
    path('company/<str:company_id>/', scoped_views.CompanyEventListAPI.as_view()),

    # ── Admin (BEFORE <event_id> wildcard) ───────────────────
    path('admin/', admin_views.AdminEventListAPI.as_view()),
    path('admin/<str:event_id>/approve/', admin_views.AdminEventApproveAPI.as_view()),
    path('admin/<str:event_id>/reject/', admin_views.AdminEventRejectAPI.as_view()),
    path('admin/<str:event_id>/feature/', admin_views.AdminEventFeatureAPI.as_view()),

    # ── Mentor & Campus Approvals ────────────────────────────
    path('mentor/<str:event_id>/approve/', manage_views.MentorEventApproveAPI.as_view()),
    path('mentor/<str:event_id>/reject/', manage_views.MentorEventRejectAPI.as_view()),
    path('campus/<str:event_id>/approve/', manage_views.CampusEventApproveAPI.as_view()),
    path('campus/<str:event_id>/reject/', manage_views.CampusEventRejectAPI.as_view()),
    path('company/<str:event_id>/approve/', manage_views.CompanyEventApproveAPI.as_view()),
    path('company/<str:event_id>/reject/', manage_views.CompanyEventRejectAPI.as_view()),

    # ── Manage (BEFORE <event_id> wildcard) ──────────────────
    path('manage/', manage_views.ManageEventListCreateAPI.as_view()),
    path('manage/<str:event_id>/publish/', manage_views.ManageEventPublishAPI.as_view()),

    # Co-owners
    path('manage/<str:event_id>/co-owners/', manage_views.ManageEventCoOwnerAPI.as_view()),
    path('manage/<str:event_id>/co-owners/<str:co_owner_id>/', manage_views.ManageEventCoOwnerRemoveAPI.as_view()),

    # Collaborators — specific sub-actions BEFORE the remove wildcard
    path('manage/<str:event_id>/collaborators/', manage_views.ManageEventCollaboratorAPI.as_view()),
    path('manage/<str:event_id>/collaborators/<str:collaborator_id>/accept/', manage_views.ManageEventCollaboratorAcceptAPI.as_view()),
    path('manage/<str:event_id>/collaborators/<str:collaborator_id>/reject/', manage_views.ManageEventCollaboratorRejectAPI.as_view()),
    path('manage/<str:event_id>/collaborators/<str:collaborator_id>/', manage_views.ManageEventCollaboratorRemoveAPI.as_view()),

    # Event Tasks
    path('manage/<str:event_id>/tasks/meta/', task_views.EventTaskMetaAPI.as_view()),
    path('manage/<str:event_id>/tasks/<str:task_id>/', task_views.EventTaskDetailAPI.as_view()),
    path('manage/<str:event_id>/tasks/', task_views.EventTaskListCreateAPI.as_view()),

    # Event Analytics
    path('manage/<str:event_id>/analytics/', analytics_views.EventAnalyticsAPI.as_view()),

    # Manage event detail (GET / PUT / PATCH / DELETE)
    path('manage/<str:event_id>/', manage_views.ManageEventDetailAPI.as_view()),

    # ── User Dashboard ───────────────────────────────
    path('my-invites/', manage_views.MyEventInvitesAPI.as_view()),

    # ── Public (wildcards last) ───────────────────────────────
    path('calendar/', public_views.EventCalendarAPI.as_view()),
    path('featured/', public_views.EventFeaturedAPI.as_view()),
    path('is-featured/', public_views.EventFeaturedAPI.as_view()),
    path('tasks/', public_views.EventTaskPublicListAPI.as_view()),
    path('<str:event_id>/interest/', public_views.EventInterestAPI.as_view()),
    path('<str:event_id>/', public_views.EventDetailAPI.as_view()),
    path('', public_views.EventListAPI.as_view()),
]
