from django.db import models


# Create your models here.

# class User(models.Model):
#     id = models.CharField(primary_key=True,max_length=36,null=False)
#     discord_id = models.CharField(max_length=36,null=False)
#     mu_id = models.CharField(max_length=25,null=False)
#     first_name = models.CharField(max_length=75,null=False)
#     last_name = models.CharField(max_length=75,null=True)
#     email = models.CharField(max_length=200,null=False)
#     mobile = models.CharField(max_length=15,null=False)
#     admin = models.BooleanField(default=False,null=False)
#     active = models.BooleanField(default=False,null=False)
#     district_id = models.CharField(max_length=36,null=True)
#     creator_id = models.CharField(max_length=36,null=False)
#     created_date = models.DateTimeField(null=False)

#     class Meta:
#         db_table = 'user'


class Colleges(models.Model):
    college_name = models.CharField(unique=True, max_length=255)
    college_code = models.CharField(unique=True, max_length=10)
    university = models.CharField(max_length=255)
    zone_code = models.CharField(max_length=10)
    district = models.CharField(max_length=50)
    state = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'colleges'


class Students(models.Model):
    user_id = models.AutoField(primary_key=True)
    fullname = models.CharField(max_length=150, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    muid = models.CharField(max_length=100, blank=True, null=True)
    mobile = models.BigIntegerField(blank=True, null=True)
    college = models.ForeignKey(Colleges, models.DO_NOTHING, db_column='college', to_field='college_code', blank=True,
                                null=True)
    area_of_interest = models.TextField(blank=True, null=True)
    created_on = models.DateTimeField(blank=True, null=True)
    discord_id = models.BigIntegerField(unique=True, blank=True, null=True)
    git_id = models.CharField(max_length=255, blank=True, null=True)
    uuid = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'students'


class StudentKarma(models.Model):
    user_id = models.IntegerField(primary_key=True)
    score = models.BigIntegerField(blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    daily_karma_limit = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'student_karma'
