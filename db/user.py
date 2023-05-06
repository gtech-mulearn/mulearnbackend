from django.db import models


class User(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    discord_id = models.CharField(
        unique=True, max_length=36, blank=True, null=True)
    mu_id = models.CharField(unique=True, max_length=100)
    first_name = models.CharField(max_length=75)
    last_name = models.CharField(max_length=75, blank=True, null=True)
    email = models.CharField(unique=True, max_length=200)
    password = models.CharField(max_length=200, blank=True, null=True)
    mobile = models.CharField(max_length=15)
    gender = models.CharField(max_length=10, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    admin = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    exist_in_guild = models.BooleanField(default=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user'

    @property
    def full_name(self):
        if self.last_name is None:
            return self.first_name

        return self.first_name + self.last_name


class Role(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=75)
    description = models.CharField(max_length=300, blank=True, null=True)
    updated_by = models.ForeignKey(
        User, models.DO_NOTHING, db_column='updated_by', related_name='role_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User, models.DO_NOTHING, db_column='created_by', related_name='role_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'role'


class UserRoleLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, models.DO_NOTHING, related_name='user_role_link_user')
    role = models.ForeignKey(Role, models.DO_NOTHING)
    verified = models.IntegerField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by',
                                   related_name='user_role_link_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_role_link'


class Github(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, models.DO_NOTHING)
    username = models.CharField(max_length=100)
    updated_by = models.CharField(max_length=36)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'github'


class ForgotPassword(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.OneToOneField(User, models.DO_NOTHING)
    expiry = models.DateTimeField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'forgot_password'
