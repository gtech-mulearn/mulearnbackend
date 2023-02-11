from django.db import models

# Create your models here.

class User(models.Model):
    id = models.CharField(primary_key=True,max_length=36,null=False)
    discord_id = models.CharField(max_length=36,null=False)
    mu_id = models.CharField(max_length=25,null=False)
    first_name = models.CharField(max_length=75,null=False)
    last_name = models.CharField(max_length=75,null=True)
    email = models.CharField(max_length=200,null=False)
    mobile = models.CharField(max_length=15,null=False)
    admin = models.BooleanField(default=False,null=False)
    active = models.BooleanField(default=False,null=False)
    district_id = models.CharField(max_length=36,null=True)
    creator_id = models.CharField(max_length=36,null=False)
    created_date = models.DateTimeField(null=False)

    class Meta:
        db_table = 'user'


class TotalKarma(models.Model):
    id = models.CharField(primary_key=True,max_length=36,null=False)
    user_id = models.ForeignKey(User,null=False,on_delete=models.CASCADE)
    karma = models.BigIntegerField(null=False)
    updated_date = models.DateField(null=False)

    class Meta:
        db_table = 'total_karma'