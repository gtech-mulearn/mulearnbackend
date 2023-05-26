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
    name = models.CharField(max_length=75)
    discord_id = models.CharField(max_length=36)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'channel'


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


class Github(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey('User', models.DO_NOTHING)
    username = models.CharField(max_length=100)
    updated_by = models.CharField(max_length=36)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'github'


class InterestGroup(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=75)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'interest_group'


class KarmaActivityLog(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    karma = models.IntegerField()
    task = models.ForeignKey('TaskList', models.DO_NOTHING)
    task_message_id = models.CharField(max_length=36)
    lobby_message_id = models.CharField(max_length=36, blank=True, null=True)
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
    user = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)
    otp = models.IntegerField(blank=True, null=True)
    expiry = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'otp_verification'


class Portal(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    portal_key = models.CharField(max_length=36)
    name = models.CharField(max_length=75)
    link = models.CharField(max_length=100, blank=True, null=True)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'portal'


class PortalUserAuth(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    portal = models.ForeignKey(Portal, models.DO_NOTHING)
    user = models.ForeignKey('User', models.DO_NOTHING)
    is_authenticated = models.IntegerField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'portal_user_auth'


class PortalUserMailValidate(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    portal = models.ForeignKey(Portal, models.DO_NOTHING)
    user = models.ForeignKey('User', models.DO_NOTHING)
    token = models.CharField(max_length=36)
    expiry = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'portal_user_mail_validate'


class Role(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    discord_id = models.CharField(max_length=36)
    title = models.CharField(max_length=75)
    description = models.CharField(max_length=300, blank=True, null=True)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'role'


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


class TaskList(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    hashtag = models.CharField(max_length=75)
    title = models.CharField(max_length=75)
    description = models.CharField(max_length=200, blank=True, null=True)
    karma = models.IntegerField(blank=True, null=True)
    channel = models.ForeignKey(Channel, models.DO_NOTHING)
    type = models.ForeignKey('TaskType', models.DO_NOTHING)
    active = models.IntegerField()
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
    long_url = models.CharField(max_length=2000, blank=True, null=True)
    short_url = models.CharField(max_length=300, blank=True, null=True)
    updated_by = models.ForeignKey('User', models.DO_NOTHING, db_column='updated_by', blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey('User', models.DO_NOTHING, db_column='created_by', blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'url_shortener'


class User(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    discord_id = models.CharField(unique=True, max_length=36)
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

    class Meta:
        managed = False
        db_table = 'user'


class UserIgLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, models.DO_NOTHING)
    ig = models.ForeignKey(InterestGroup, models.DO_NOTHING)
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_ig_link'


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


class UserVerificationOtp(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    otp = models.IntegerField(blank=True, null=True)
    expiry = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_verification_otp'


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
