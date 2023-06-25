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
    exist_in_guild = models.BooleanField(default=False)
    profile_pic = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user'

    @property
    def fullname(self):
        if self.last_name is None:
            return self.first_name

        return f"{self.first_name} {self.last_name}"


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
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_role_link_user')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    verified = models.BooleanField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='created_by',
                                   related_name='user_role_link_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_role_link'


class Github(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=100)
    updated_by = models.CharField(max_length=36)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'github'


class ForgotPassword(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    expiry = models.DateTimeField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'forgot_password'


class UserSettings(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='updated_by',
                                   related_name='user_settings_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='created_by',
                                   related_name='user_settings_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_settings'
