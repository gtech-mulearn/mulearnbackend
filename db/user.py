import uuid

from django.db import models


class User(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    discord_id = models.CharField(
        unique=True, max_length=36, blank=True, null=True)
    muid = models.CharField(unique=True, max_length=100)
    first_name = models.CharField(max_length=75)
    last_name = models.CharField(max_length=75, blank=True, null=True)
    email = models.EmailField(unique=True, max_length=200)
    password = models.CharField(max_length=200, blank=True, null=True)
    mobile = models.CharField(unique=True, max_length=15)
    gender = models.CharField(max_length=10, blank=True, null=True, choices=["Male", "Female"])
    dob = models.DateField(blank=True, null=True)
    admin = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    exist_in_guild = models.BooleanField(default=False)
    profile_pic = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'user'

    @property
    def fullname(self):
        if self.last_name is None:
            return self.first_name

        return f"{self.first_name} {self.last_name}"


class UserReferralLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_referral_link_user')
    referral = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_referral_link_referral')
    is_coin = models.BooleanField(default=False)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_referral_link_updated_by',
                                   db_column='updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_referral_link_created_by',
                                   db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'user_referral_link'


class Role(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=75)
    description = models.CharField(max_length=300, blank=True, null=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='updated_by', related_name='role_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='created_by', related_name='role_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'role'


class UserRoleLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_role_link_user')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    verified = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='created_by',
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
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='created_by',
                                   related_name='socials_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='updated_by',
                                   related_name='socials_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True, auto_now=True)

    class Meta:
        managed = False
        db_table = 'socials'


class ForgotPassword(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    expiry = models.DateTimeField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'forgot_password'


class UserSettings(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="user_settings_user")
    is_public = models.BooleanField(default=False)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='updated_by',
                                   related_name='user_settings_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='created_by',
                                   related_name='user_settings_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'user_settings'


class DynamicRole(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    type = models.CharField(max_length=50)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, db_column='role', related_name='dynamic_role_role')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='updated_by',
                                   related_name='dynamic_role_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='created_by',
                                   related_name='dynamic_role_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'dynamic_role'


class DynamicUser(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    type = models.CharField(max_length=50)
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='dynamic_user_user')
    updated_by = models.ForeignKey('User', on_delete=models.CASCADE, db_column='updated_by',
                                   related_name='dynamic_user_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('User', on_delete=models.CASCADE, db_column='created_by',
                                   related_name='dynamic_user_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'dynamic_user'
