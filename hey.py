# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Channel(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(unique=True, max_length=75)
    discord_id = models.CharField(max_length=36)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'channel'


class College(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    level = models.IntegerField()
    org = models.ForeignKey('Organization', models.DO_NOTHING)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'college'


class Country(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=75)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'country'


class Department(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=100)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'department'


class Device(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    browser = models.CharField(max_length=36)
    os = models.CharField(max_length=36)
    user = models.ForeignKey('User', models.DO_NOTHING)
    last_log_in = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'device'


class District(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=75)
    zone = models.ForeignKey('Zone', models.DO_NOTHING)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'district'


class ForgotPassword(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey('User', models.DO_NOTHING)
    expiry = models.DateTimeField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'forgot_password'


class Hackathon(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=100)
    tagline = models.CharField(max_length=150, blank=True, null=True)
    description = models.CharField(max_length=5000, blank=True, null=True)
    participant_count = models.IntegerField(blank=True, null=True)
    type = models.CharField(max_length=8, blank=True, null=True)
    website = models.CharField(max_length=200, blank=True, null=True)
    org = models.ForeignKey('Organization', models.DO_NOTHING, blank=True, null=True)
    district = models.ForeignKey(District, models.DO_NOTHING, blank=True, null=True)
    place = models.CharField(max_length=255, blank=True, null=True)
    event_logo = models.CharField(max_length=200, blank=True, null=True)
    banner = models.CharField(max_length=200, blank=True, null=True)
    is_open_to_all = models.IntegerField(blank=True, null=True)
    application_start = models.DateTimeField(blank=True, null=True)
    application_ends = models.DateTimeField(blank=True, null=True)
    event_start = models.DateTimeField(blank=True, null=True)
    event_end = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'hackathon'


class HackathonForm(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    hackathon = models.ForeignKey(Hackathon, models.DO_NOTHING)
    field_name = models.CharField(max_length=255)
    field_type = models.CharField(max_length=50)
    is_required = models.IntegerField(blank=True, null=True)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'hackathon_form'


class HackathonOrganiserLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    organiser = models.ForeignKey('User', models.DO_NOTHING)
    hackathon = models.ForeignKey(Hackathon, models.DO_NOTHING)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'hackathon_organiser_link'


class HackathonSubmission(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.OneToOneField('User', models.DO_NOTHING)
    hackathon = models.ForeignKey(Hackathon, models.DO_NOTHING)
    data = models.CharField(max_length=2000)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'hackathon_submission'


class Integration(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=255)
    token = models.CharField(max_length=400)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'integration'


class IntegrationAuthorization(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    integration = models.ForeignKey(Integration, models.DO_NOTHING)
    user = models.OneToOneField('User', models.DO_NOTHING)
    integration_value = models.CharField(unique=True, max_length=255)
    verified = models.IntegerField()
    updated_at = models.DateTimeField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'integration_authorization'


class InterestGroup(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=75)
    code = models.CharField(unique=True, max_length=5, blank=True, null=True)
    icon = models.CharField(max_length=10, blank=True, null=True)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'interest_group'


class KarmaActivityLog(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey('User', models.DO_NOTHING)
    karma = models.IntegerField()
    task = models.ForeignKey('TaskList', models.DO_NOTHING)
    task_message_id = models.CharField(max_length=36)
    lobby_message_id = models.CharField(max_length=36, blank=True, null=True)
    dm_message_id = models.CharField(max_length=36, blank=True, null=True)
    peer_approved = models.IntegerField(blank=True, null=True)
    peer_approved_by = models.CharField(max_length=36, blank=True, null=True)
    appraiser_approved = models.IntegerField(blank=True, null=True)
    appraiser_approved_by = models.CharField(max_length=36, blank=True, null=True)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'karma_activity_log'


class LearningCircle(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=255)
    circle_code = models.CharField(unique=True, max_length=10)
    ig = models.ForeignKey(InterestGroup, models.DO_NOTHING)
    org = models.ForeignKey('Organization', models.DO_NOTHING)
    meet_place = models.CharField(max_length=255, blank=True, null=True)
    meet_time = models.DateTimeField(blank=True, null=True)
    day = models.CharField(max_length=20, blank=True, null=True)
    note = models.CharField(max_length=500, blank=True, null=True)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'learning_circle'


class Level(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    level_order = models.IntegerField()
    name = models.CharField(unique=True, max_length=36)
    karma = models.IntegerField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'level'


class Notification(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey('User', models.DO_NOTHING)
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=200)
    button = models.CharField(max_length=10, blank=True, null=True)
    url = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')

    class Meta:
        managed = False
        db_table = 'notification'


class OrgAffiliation(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=75)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'org_affiliation'


class OrgDiscordLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    discord_id = models.CharField(unique=True, max_length=36)
    org = models.OneToOneField('Organization', models.DO_NOTHING)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'org_discord_link'


class Organization(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=100)
    code = models.CharField(unique=True, max_length=12)
    org_type = models.CharField(max_length=25)
    affiliation = models.ForeignKey(OrgAffiliation, models.DO_NOTHING, blank=True, null=True)
    district = models.ForeignKey(District, models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'organization'


class OtpVerification(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey('User', models.DO_NOTHING)
    otp = models.IntegerField()
    expiry = models.DateTimeField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'otp_verification'


class Role(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=75)
    description = models.CharField(max_length=300, blank=True, null=True)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'role'


class Socials(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey('User', models.DO_NOTHING)
    github = models.CharField(max_length=60, blank=True, null=True)
    facebook = models.CharField(max_length=60, blank=True, null=True)
    instagram = models.CharField(max_length=60, blank=True, null=True)
    linkedin = models.CharField(max_length=60, blank=True, null=True)
    dribble = models.CharField(max_length=60, blank=True, null=True)
    behance = models.CharField(max_length=60, blank=True, null=True)
    stackoverflow = models.CharField(max_length=60, blank=True, null=True)
    medium = models.CharField(max_length=60, blank=True, null=True)
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'socials'


class State(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=75)
    country = models.ForeignKey(Country, models.DO_NOTHING)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'state'


class SystemSetting(models.Model):
    key = models.CharField(primary_key=True, max_length=100)
    value = models.CharField(max_length=100)
    updated_at = models.DateTimeField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'system_setting'


class TaskList(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    hashtag = models.CharField(max_length=75)
    title = models.CharField(max_length=75)
    description = models.CharField(max_length=200, blank=True, null=True)
    karma = models.IntegerField(blank=True, null=True)
    channel = models.ForeignKey(Channel, models.DO_NOTHING)
    type = models.ForeignKey('TaskType', models.DO_NOTHING)
    org = models.ForeignKey(Organization, models.DO_NOTHING, blank=True, null=True)
    level = models.ForeignKey(Level, models.DO_NOTHING, blank=True, null=True)
    ig = models.ForeignKey(InterestGroup, models.DO_NOTHING, blank=True, null=True)
    active = models.IntegerField()
    variable_karma = models.IntegerField()
    usage_count = models.IntegerField(blank=True, null=True)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'task_list'


class TaskType(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=75)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'task_type'


class TotalKarma(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.OneToOneField('User', models.DO_NOTHING)
    karma = models.BigIntegerField()
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'total_karma'


class UrlShortener(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=100)
    short_url = models.CharField(unique=True, max_length=100)
    long_url = models.CharField(max_length=500)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()
    count = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'url_shortener'


class UrlShortenerTracker(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    ip_address = models.CharField(max_length=45)
    browser = models.CharField(max_length=255, blank=True, null=True)
    operating_system = models.CharField(max_length=255, blank=True, null=True)
    version = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    device_type = models.CharField(max_length=255, blank=True, null=True)
    url_shortener = models.ForeignKey(UrlShortener, models.DO_NOTHING, blank=True, null=True)
    city = models.CharField(max_length=36, blank=True, null=True)
    region = models.CharField(max_length=36, blank=True, null=True)
    country = models.CharField(max_length=36, blank=True, null=True)
    location = models.CharField(max_length=36, blank=True, null=True)
    referrer = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'url_shortener_tracker'


class User(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    discord_id = models.CharField(unique=True, max_length=36, blank=True, null=True)
    mu_id = models.CharField(unique=True, max_length=100)
    first_name = models.CharField(max_length=75)
    last_name = models.CharField(max_length=75, blank=True, null=True)
    email = models.CharField(unique=True, max_length=200)
    password = models.CharField(max_length=200, blank=True, null=True)
    mobile = models.CharField(max_length=15)
    gender = models.CharField(max_length=10, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    admin = models.IntegerField()
    active = models.IntegerField()
    exist_in_guild = models.IntegerField()
    created_at = models.DateTimeField()
    profile_pic = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user'


class UserCircleLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, models.DO_NOTHING)
    circle = models.ForeignKey(LearningCircle, models.DO_NOTHING)
    lead = models.IntegerField(blank=True, null=True)
    accepted = models.IntegerField(blank=True, null=True)
    accepted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_circle_link'


class UserIgLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, models.DO_NOTHING)
    ig = models.ForeignKey(InterestGroup, models.DO_NOTHING)
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_ig_link'


class UserLvlLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.OneToOneField(User, models.DO_NOTHING)
    level = models.ForeignKey(Level, models.DO_NOTHING)
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_lvl_link'


class UserOrganizationLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, models.DO_NOTHING)
    org = models.ForeignKey(Organization, models.DO_NOTHING)
    department = models.ForeignKey(Department, models.DO_NOTHING, blank=True, null=True)
    graduation_year = models.CharField(max_length=10, blank=True, null=True)
    verified = models.IntegerField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_organization_link'


class UserReferralLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, models.DO_NOTHING)
    referral = models.ForeignKey(User, models.DO_NOTHING)
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_referral_link'


class UserRoleLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, models.DO_NOTHING)
    role = models.ForeignKey(Role, models.DO_NOTHING)
    verified = models.IntegerField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_role_link'


class UserSettings(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, models.DO_NOTHING)
    is_public = models.IntegerField()
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_settings'


class VoucherLog(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    code = models.CharField(max_length=15)
    user = models.ForeignKey(User, models.DO_NOTHING)
    task = models.ForeignKey(TaskList, models.DO_NOTHING)
    karma = models.IntegerField()
    mail = models.CharField(max_length=200)
    week = models.CharField(max_length=2)
    month = models.CharField(max_length=10)
    claimed = models.IntegerField()
    updated_by = models.CharField(max_length=36)
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'voucher_log'


class Zone(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=75)
    state = models.ForeignKey(State, models.DO_NOTHING)
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'zone'
