import uuid

from django.core.files.storage import FileSystemStorage
from django.db import models

from django.conf import settings

from .managers import user_manager

# from .task import UserIgLink
from decouple import config as decouple_config


# fmt: off
# noinspection PyPep8

class User(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    discord_id = models.CharField(unique=True, max_length=36, blank=True, null=True)
    muid = models.CharField(unique=True, max_length=100)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True, max_length=200)
    password = models.CharField(max_length=200, blank=True, null=True)
    mobile = models.CharField(unique=True, max_length=15, blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True, choices=[("Male", "Male"), ("Female", "Female"), ("Other", "Other"), ("Prefer not to say", "Prefer not to say")])
    dob = models.DateField(blank=True, null=True)
    admin = models.BooleanField(default=False)
    exist_in_guild = models.BooleanField(default=False)
    district = models.ForeignKey("District", on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    suspended_at = models.DateTimeField(blank=True, null=True)
    interested_in_work = models.BooleanField(default=False)
    interested_in_gig_work = models.BooleanField(default=False)
    suspended_by = models.ForeignKey("self", on_delete=models.SET(settings.SYSTEM_ADMIN_ID), blank=True, null=True,
                                     related_name="user_suspended_by_user", db_column="suspended_by", default=None)
    objects = user_manager.ActiveUserManager()
    every = models.Manager()

    class Meta:
        managed = False
        db_table = 'user'

    @property
    def profile_pic(self):
        fs = FileSystemStorage()
        path = f'user/profile/{self.id}.png'
        if fs.exists(path):
            return f"{decouple_config('BE_DOMAIN_NAME')}{fs.url(path)}"

    @property
    def cover_pic(self):
        fs = FileSystemStorage()
        path = f'user/cover/{self.id}.png'
        if fs.exists(path):
            return f"{decouple_config('BE_DOMAIN_NAME')}{fs.url(path)}"

    def save(self, *args, **kwargs):
        if self.muid is None:
            full_name = self.full_name.replace(" ", "-").lower()
            self.muid = f"{full_name}@mulearn"

            counter = 0
            while User.objects.filter(muid=self.muid).exists():
                counter += 1
                self.muid = f"{full_name}-{counter}@mulearn"

        return super().save(*args, **kwargs)

class UserDomains(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_domains")
    domain_name = models.CharField(max_length=50, null=False, blank=False)
    # is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'user_domains'

class UserEndgoals(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False, related_name="user_endgoals")
    endgoal_name = models.CharField(max_length=50, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'user_endgoals'

# class UserInterests(models.Model):
#     id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     choosen_interests = models.JSONField(max_length=100)
#     other_interests = models.JSONField(max_length=100, blank=True, null=True)
#     choosen_endgoals = models.JSONField(max_length=100)
#     other_endgoals = models.JSONField(max_length=100, blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         managed = False
#         db_table = 'user_interests'
        

class UserMentor(models.Model):
    """
    A user's single mentor profile row (one per user). Which tiers a mentor
    actually holds is NOT stored here — it's derived from active
    MentorScopeGrant rows. Pending/rejected applications live in
    MentorApplication, not here. See MentorApplication and MentorScopeGrant.
    """

    class MentorTier(models.TextChoices):
        IG_MENTOR      = 'IG_MENTOR',      'IG Mentor'       # linked to specific IG(s)
        MENTOR         = 'MENTOR',         'Mentor'           # platform-wide global mentor
        COMPANY_MENTOR = 'COMPANY_MENTOR', 'Company Mentor'  # scoped to a Company org
        CAMPUS_MENTOR  = 'CAMPUS_MENTOR',  'Campus Mentor'   # scoped to a College org

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='user_mentor_user'
    )

    about = models.CharField(max_length=1000, blank=True, null=True)

    expertise = models.TextField(blank=True, null=True)

    reason = models.CharField(max_length=1000, blank=True, null=True)

    hours = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    deactivated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='deactivated_by',
        related_name='user_mentor_deactivated_by_set'
    )

    deactivated_at = models.DateTimeField(blank=True, null=True)

    deactivation_reason = models.CharField(max_length=500, blank=True, null=True)

    updated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='updated_by',
        related_name='user_mentor_updated_by_set'
    )

    updated_at = models.DateTimeField(blank=True, null=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='created_by',
        related_name='user_mentor_created_by_set'
    )

    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_mentor'


class MentorApplication(models.Model):
    """
    A single application or nomination for a mentor tier. Pending review
    state lives here, separate from both the mentor's profile (UserMentor)
    and any authority it eventually grants (MentorScopeGrant). A user may
    have many of these over time (different tiers, different companies,
    resubmissions after rejection).
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    class SourceType(models.TextChoices):
        SELF_APPLIED     = 'SELF_APPLIED',     'Self Applied'
        OWNER_NOMINATED  = 'OWNER_NOMINATED',  'Owner Nominated'
        LEAD_NOMINATED   = 'LEAD_NOMINATED',   'Lead Nominated'
        ADMIN_ASSIGNED   = 'ADMIN_ASSIGNED',   'Admin Assigned'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='mentor_applications'
    )

    tier = models.CharField(max_length=30, choices=UserMentor.MentorTier.choices, db_column='mentor_tier')

    org = models.ForeignKey(
        'db.Organization',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='org_id',
        related_name='org_mentor_applications'
    )

    # JSON list of IG UUIDs applicant expressed interest in (IG_MENTOR tier).
    preferred_ig_ids = models.JSONField(null=True, blank=True)

    # Profile-field snapshot submitted with this specific application.
    about = models.CharField(max_length=1000, blank=True, null=True)
    expertise = models.TextField(blank=True, null=True)
    reason = models.CharField(max_length=1000, blank=True, null=True)
    hours = models.PositiveIntegerField(default=0)

    source = models.CharField(max_length=20, choices=SourceType.choices)

    nominated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='nominated_by',
        related_name='mentor_applications_nominated'
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING
    )

    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='verified_by_id',
        related_name='mentor_applications_verified_by_set'
    )

    verified_at = models.DateTimeField(blank=True, null=True)

    verification_note = models.CharField(max_length=1000, blank=True, null=True)

    nomination_expires_at = models.DateTimeField(blank=True, null=True)

    resulting_grant = models.ForeignKey(
        'MentorScopeGrant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='resulting_grant_id',
        related_name='source_application'
    )

    updated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='updated_by_id',
        related_name='mentor_applications_updated_by_set'
    )

    updated_at = models.DateTimeField(blank=True, null=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='created_by_id',
        related_name='mentor_applications_created_by_set'
    )

    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mentor_application'


class MentorScopeGrant(models.Model):
    """
    A single unit of mentor authority: "this mentor may act as X within
    scope Y". Holding an active grant for (scope_type, scope_id) IS what
    makes a mentor a member of that tier — tiers are not stored on
    UserMentor. Additive and independent per (scope_type, scope_id) —
    granting or revoking one grant never affects any other grant for the
    same mentor, and never touches identity records like UserOrganizationLink.
    """

    class ScopeType(models.TextChoices):
        COMPANY_MENTOR = 'COMPANY_MENTOR', 'Company Mentor'
        IG_MENTOR      = 'IG_MENTOR',      'IG Mentor'
        CAMPUS_MENTOR  = 'CAMPUS_MENTOR',  'Campus Mentor'
        MENTOR         = 'MENTOR',         'Mentor'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)

    mentor = models.ForeignKey(
        UserMentor,
        on_delete=models.CASCADE,
        db_column='mentor_id',
        related_name='scope_grants'
    )

    scope_type = models.CharField(max_length=14, choices=ScopeType.choices)

    # NULL for scope types that aren't org/IG scoped in the future;
    # currently always set (org id for COMPANY_MENTOR/CAMPUS_MENTOR, ig id
    # for IG_MENTOR).
    scope_id = models.CharField(max_length=36, null=True, blank=True)

    # Which application resulted in this grant, if any (traceability).
    application = models.ForeignKey(
        MentorApplication,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='application_id',
        related_name='resulting_grants'
    )

    is_active = models.BooleanField(default=True)

    expires_at = models.DateTimeField(null=True, blank=True)

    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='granted_by',
        related_name='mentor_grants_given'
    )

    granted_at = models.DateTimeField()

    revoked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='revoked_by',
        related_name='mentor_grants_revoked'
    )

    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'mentor_scope_grant'


class UserReferralLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_referral_link_user')
    referral = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_referral_link_referral')
    is_coin = models.BooleanField(default=False)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
                                   related_name='user_referral_link_updated_by', db_column='updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
                                   related_name='user_referral_link_created_by', db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'user_referral_link'


class Role(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=75)
    description = models.CharField(max_length=300, blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='role_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='role_created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    is_execom_role = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = 'role'


class UserRoleLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_role_link_user')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    # IG-scoped role support: NULL = global platform role, SET = IG-specific role
    ig = models.ForeignKey(
        'db.InterestGroup', on_delete=models.CASCADE,
        null=True, blank=True, db_column='ig_id',
        related_name='user_role_link_ig'
    )
    verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='revoked_by', related_name='user_role_link_revoked_by'
    )
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='user_role_link_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'user_role_link'


class Socials(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    github = models.CharField(max_length=60, blank=True, null=True)
    facebook = models.CharField(max_length=60, blank=True, null=True)
    instagram = models.CharField(max_length=60, blank=True, null=True)
    linkedin = models.CharField(max_length=60, blank=True, null=True)
    dribble = models.CharField(max_length=60, blank=True, null=True)
    behance = models.CharField(max_length=60, blank=True, null=True)
    stackoverflow = models.CharField(max_length=60, blank=True, null=True)
    medium = models.CharField(max_length=60, blank=True, null=True)
    hackerrank = models.CharField(max_length=60, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='socials_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='socials_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True, auto_now=True)

    class Meta:
        managed = False
        db_table = 'socials'


class ForgotPassword(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID))
    expiry = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'forgot_password'


class UserSettings(models.Model):

    class PersonaType(models.TextChoices):
        LEARNER = 'learner', 'Learner'
        MENTOR = 'mentor', 'Mentor'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='user_settings_user'
    )

    is_public = models.BooleanField(default=False)

    is_userterms_approved = models.BooleanField(default=False)

    # Active contextual persona state
    active_persona = models.CharField(
        max_length=10,
        choices=PersonaType.choices,
        default=PersonaType.LEARNER
    )

    active_role_link = models.ForeignKey(
        'UserRoleLink',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='active_role_link_id',
        related_name='user_settings_active_role_link'
    )

    active_ig = models.ForeignKey(
        'db.InterestGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='active_ig_id',
        related_name='user_settings_active_ig'
    )

    # Generic active-scope pointer for persona switching, mirrors
    # MentorScopeGrant.ScopeType/scope_id. Used instead of active_ig for
    # non-IG mentor tiers (company/campus/global) since active_ig can only
    # ever represent an IG.
    active_scope_type = models.CharField(max_length=20, null=True, blank=True)

    active_scope_id = models.CharField(max_length=36, null=True, blank=True)

    last_persona_switched_at = models.DateTimeField(
        null=True,
        blank=True
    )

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='updated_by',
        related_name='user_settings_updated_by'
    )

    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='created_by',
        related_name='user_settings_created_by'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'user_settings'


class DynamicRole(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    type = models.CharField(max_length=50)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, db_column='role', related_name='dynamic_role_role')
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='dynamic_role_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='dynamic_role_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'dynamic_role'


class DynamicUser(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    type = models.CharField(max_length=50)
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='dynamic_user_user')
    updated_by = models.ForeignKey('User', on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='dynamic_user_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('User', on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='dynamic_user_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'dynamic_user'


class UserCouponLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='usercouponlink_user')
    coupon = models.CharField(max_length=15)
    type = models.CharField(max_length=36)
    created_by = models.ForeignKey('User', on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='usercouponlink_created_by_set')
    created_at = models.DateTimeField()

    class Meta:
        managed = False

        db_table = 'user_coupon_link'
