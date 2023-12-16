import uuid

from django.db import models

from django.conf import settings
from .user import User

# fmt: off
# noinspection PyPep8

class Country(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name = models.CharField(max_length=75, null=False, unique=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='country_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='country_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'country'


class State(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name = models.CharField(max_length=75)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='state_country')
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='state_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='state_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'state'


class Zone(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name = models.CharField(max_length=75)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='zone_state')
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='zone_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='zone_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'zone'


class District(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name = models.CharField(max_length=75)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="district_zone")
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='district_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='district_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'district'


class OrgAffiliation(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4())
    title = models.CharField(max_length=75)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by', related_name='org_affiliation_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by', related_name='org_affiliation_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'org_affiliation'


class Organization(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4())
    title = models.CharField(max_length=100)
    code = models.CharField(unique=True, max_length=12)
    org_type = models.CharField(max_length=25)
    affiliation = models.ForeignKey(OrgAffiliation, on_delete=models.CASCADE, blank=True, null=True, related_name='organization_affiliation')
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='organization_district')
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='organization_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='organization_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'organization'


class Department(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4())
    title = models.CharField(max_length=100)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='department_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='department_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'department'


class College(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4())
    level = models.IntegerField(default=0)
    org = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='college_org', unique=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='college_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='college_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'college'


class OrgDiscordLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    discord_id = models.CharField(unique=True, max_length=36)
    org = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='org_discord_link_org_id')
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='org_discord_link_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='org_discord_link_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'org_discord_link'


class UserOrganizationLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_organization_link_user')
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='user_organization_link_org')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, blank=True, null=True,
                                   related_name='user_organization_link_department')
    graduation_year = models.CharField(max_length=10, blank=True, null=True)
    verified = models.BooleanField()
    is_alumni = models.IntegerField(blank=True, null=True, default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='user_organization_link_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'user_organization_link'


class OrgKarmaType(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4())
    title = models.CharField(max_length=75)
    karma = models.IntegerField()
    description = models.CharField(max_length=200, blank=True, null=True)
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column='updated_by',
                                   related_name='org_karma_type_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by',
                                   related_name='org_karma_type_created_by')
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'org_karma_type'


class OrgKarmaLog(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4())
    org = models.ForeignKey(Organization, models.DO_NOTHING, related_name='org_karma_log_org')
    karma = models.IntegerField()
    type = models.ForeignKey(OrgKarmaType, models.DO_NOTHING, db_column='type', related_name='org_karma_log_type')
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column='updated_by',
                                   related_name='org_karma_log_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by',
                                   related_name='org_karma_log_created_by')
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'org_karma_log'

    @property
    def total_karma(self):
        try:
            return self.user.wallet_user.karma
        except Exception as e:
            return 0

    @property
    def country(self):
        return self.org.district.zone.state.country

    @property
    def state(self):
        return self.org.district.zone.state

    @property
    def district(self):
        return self.org.district
