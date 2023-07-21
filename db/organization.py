import uuid

from django.db import models

from utils.utils import DateTimeUtils

from .user import User


class Country(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=75)
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='updated_by', related_name='country_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='created_by', related_name='country_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'country'


class State(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=75)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='updated_by', related_name='state_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='created_by', related_name='state_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'state'


class Zone(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=75)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='updated_by', related_name='zone_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='created_by', related_name='zone_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'zone'


class District(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=75)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE)
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='updated_by', related_name='district_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='created_by', related_name='district_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'district'


class OrgAffiliation(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=75)
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='updated_by', related_name='org_affiliation_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='created_by', related_name='org_affiliation_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'org_affiliation'


class Organization(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=100)
    code = models.CharField(unique=True, max_length=12)
    org_type = models.CharField(max_length=25)
    affiliation = models.ForeignKey(
        OrgAffiliation, on_delete=models.CASCADE, blank=True, null=True)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='organization_district')
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='updated_by', related_name='organization_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='created_by', related_name='organization_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'organization'


class Department(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=100)
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='updated_by', related_name='department_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='created_by', related_name='department_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'department'


class UserOrganizationLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='user_organization_link_user_id')
    org = models.ForeignKey(Organization, on_delete=models.CASCADE,
                            related_name='user_organization_link_org_id')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, blank=True, null=True,
                                   related_name='user_organization_link_department_id')
    graduation_year = models.CharField(max_length=10, blank=True, null=True)
    verified = models.BooleanField()
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='created_by', related_name='user_organization_link_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_organization_link'

    @property
    def total_karma(self):
        try:
            return self.user.total_karma_user.karma
        except Exception as e:
            return 0

    @property
    def country(self):
        return self.org.district.zone.state.country.name

    @property
    def state(self):
        return self.org.district.zone.state.name

    @property
    def district(self):
        return self.org.district.name

    @property
    def zone(self):
        return self.org.district.zone.name
