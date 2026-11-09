import uuid

from django.core.files.storage import FileSystemStorage
from django.db import models

from django.conf import settings
from django.utils import timezone

from utils.emails import normalize_email

from .managers import user_manager
from .signals import user_email_changed

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
    # NOTE: `user.last_login` is added by db-scripts alter-1.89 and is written
    # by authserver only (Django's AbstractBaseUser requires it).
    #
    # It is deliberately NOT declared here. Declaring a column before the alter
    # script has run makes Django SELECT it, and every user query then fails
    # with "Unknown column 'user.last_login'" — which would take this service
    # down the moment it deployed ahead of the schema. Nothing here reads the
    # column, so declaring it buys nothing and risks an outage.
    #
    # Add it here once alter-1.89 is applied everywhere.
    suspended_at = models.DateTimeField(blank=True, null=True)
    interested_in_work = models.BooleanField(default=False)
    interested_in_gig_work = models.BooleanField(default=False)
    suspended_by = models.ForeignKey("self", on_delete=models.SET(settings.SYSTEM_ADMIN_ID), blank=True, null=True,
                                     related_name="user_suspended_by_user", db_column="suspended_by", default=None)
    # Added by db-scripts/alter/alter-1.29.sql alongside suspended_at/suspended_by,
    # but never mirrored into either ORM — audit finding F19.
    #
    # DECLARED, NOT ENFORCED. ActiveUserManager deliberately does not filter on
    # deleted_at: nothing in either service writes these columns today, so
    # filtering would change authentication behaviour on the strength of data
    # that is always NULL. Soft-delete semantics need their own decision.
    deleted_at = models.DateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey("self", on_delete=models.SET(settings.SYSTEM_ADMIN_ID), blank=True, null=True,
                                   related_name="user_deleted_by_user", db_column="deleted_by", default=None)
    # Spec A (2026-10-12): when the CURRENT email was last proven, and how.
    # NULL means not verified. save() resets both whenever the email changes.
    email_verified_at = models.DateTimeField(blank=True, null=True)
    email_verified_via = models.CharField(max_length=20, blank=True, null=True)
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

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        # What was loaded, so save() can tell a real email change from a
        # re-save. Deferred fields are absent from __dict__.
        instance._loaded_email = instance.__dict__.get("email")
        instance._loaded_email_verified = instance.__dict__.get("email_verified_at") is not None
        return instance

    def refresh_from_db(self, using=None, fields=None, **kwargs):
        super().refresh_from_db(using=using, fields=fields, **kwargs)
        # A reload moves the baseline; otherwise the next save would see a
        # stale _loaded_email and report a change that never happened.
        if fields is None or "email" in fields:
            self._loaded_email = self.__dict__.get("email")
            self._loaded_email_verified = self.__dict__.get("email_verified_at") is not None

    def mark_email_verified_on_save(self, via):
        """The next save() writes a new email that `via` has just proven."""
        self._email_verified_by = via

    def _detect_email_change(self, update_fields):
        """(old_email, old_was_verified) if this save changes the email, else None."""
        if self._state.adding or "email" not in self.__dict__:
            return None
        if update_fields is not None and "email" not in update_fields:
            return None
        loaded = getattr(self, "_loaded_email", None)
        loaded_verified = getattr(self, "_loaded_email_verified", False)
        if loaded is None:
            row = User.every.filter(pk=self.pk).values_list("email", "email_verified_at").first()
            if row is None:
                return None
            loaded, verified_at = row
            loaded_verified = verified_at is not None
        if normalize_email(loaded) == normalize_email(self.email):
            return None
        return loaded, loaded_verified

    def save(self, *args, **kwargs):
        if self.muid is None:
            full_name = self.full_name.replace(" ", "-").lower()
            self.muid = f"{full_name}@mulearn"

            counter = 0
            while User.objects.filter(muid=self.muid).exists():
                counter += 1
                self.muid = f"{full_name}-{counter}@mulearn"

        # Spec A §3.1: a changed email never inherits verified status.
        update_fields = kwargs.get("update_fields")
        change = self._detect_email_change(update_fields)
        via = getattr(self, "_email_verified_by", None) if change else None
        if change is not None:
            self.email_verified_at = timezone.now().replace(microsecond=0) if via else None
            self.email_verified_via = via
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"email_verified_at", "email_verified_via"}

        result = super().save(*args, **kwargs)

        self._email_verified_by = None
        if change is not None:
            old_email, old_was_verified = change
            self._loaded_email = self.email
            self._loaded_email_verified = via is not None
            user_email_changed.send(
                sender=User, user=self, old_email=old_email, new_email=self.email,
                old_was_verified=old_was_verified, verified_via=via,
            )
        return result

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

class MentorApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        GRANT_REVOKED = 'GRANT_REVOKED', 'Grant Revoked'

    class MentorTier(models.TextChoices):
        IG_MENTOR      = 'IG_MENTOR',      'IG Mentor'
        MENTOR         = 'MENTOR',         'Mentor'
        COMPANY_MENTOR = 'COMPANY_MENTOR', 'Company Mentor'
        CAMPUS_MENTOR  = 'CAMPUS_MENTOR',  'Campus Mentor'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentor_applications')
    mentor_tier = models.CharField(max_length=30, choices=MentorTier.choices)
    org = models.ForeignKey('db.Organization', on_delete=models.SET_NULL, null=True, blank=True, db_column='org_id', related_name='mentor_applications')
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    reason = models.CharField(max_length=1000, blank=True, null=True)
    preferred_ig_ids = models.JSONField(null=True, blank=True)
    verification_note = models.CharField(max_length=500, blank=True, null=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='verified_by_id', related_name='verified_mentor_applications')
    verified_at = models.DateTimeField(blank=True, null=True)
    # Addon §6.2 — nomination/application expiry: a PENDING application past
    # this timestamp is auto-rejected by mu_celery.mentor_tasks.expire_stale_applications.
    nomination_expires_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='created_by_id', related_name='created_mentor_applications')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='updated_by_id', related_name='updated_mentor_applications')
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'mentor_application'

    def __str__(self):
        return f"{self.user.full_name} - {self.get_mentor_tier_display()}"


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
    class HoursCommitment(models.TextChoices):
        RANGE_0_1 = '0-1', '0-1 hours'
        RANGE_1_2 = '1-2', '1-2 hours'
        RANGE_2_5 = '2-5', '2-5 hours'
        RANGE_5_10 = '5-10', '5-10 hours'
        RANGE_10_PLUS = '10+', '10+ hours'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='mentor_profile'
    )

    about = models.CharField(max_length=1000, blank=True, null=True)

    expertise = models.TextField(blank=True, null=True)

    # Weekly time-commitment bucket the mentor self-selects (e.g. "0-1
    # hours") rather than a raw number — optional, never required for
    # registration or profile completion.
    hours = models.CharField(max_length=20, choices=HoursCommitment.choices, blank=True, null=True)

    is_active = models.BooleanField(default=True)

    updated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='updated_by',
        related_name='user_mentor_updated_by'
    )

    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='created_by',
        related_name='user_mentor_created_by'
    )

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_mentor'
class MentorScopeGrant(models.Model):
    class ScopeType(models.TextChoices):
        COMPANY_MENTOR = 'COMPANY_MENTOR', 'Company Mentor'
        IG_MENTOR      = 'IG_MENTOR',      'IG Mentor'
        CAMPUS_MENTOR  = 'CAMPUS_MENTOR',  'Campus Mentor'
        MENTOR         = 'MENTOR',         'Mentor'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    application = models.ForeignKey(
        MentorApplication,
        on_delete=models.CASCADE,
        db_column='application_id',
        related_name='scope_grants'
    )
    scope_type = models.CharField(max_length=30, choices=ScopeType.choices)
    scope_id = models.CharField(max_length=36, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='granted_by',
        related_name='mentor_grants_given'
    )
    granted_at = models.DateTimeField()
    # Addon §6.8 — optional periodic re-verification: an active grant past this
    # timestamp is auto-revoked by mu_celery.mentor_tasks.expire_stale_grants.
    # NULL means "never expires" (today's default behavior for existing grants).
    expires_at = models.DateTimeField(null=True, blank=True)
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
    linkedin = models.CharField(max_length=255, blank=True, null=True)
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


class OtpVerification(models.Model):
    """
    Login OTPs. The authserver owns this table; it is declared here only so an
    email change can revoke codes already mailed to the old inbox (spec A §3.7).
    """
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_verification_user")
    otp = models.IntegerField()
    expiry = models.DateTimeField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "otp_verification"


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
    active_scope_type = models.CharField(max_length=30, null=True, blank=True)
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
