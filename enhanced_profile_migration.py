# Migration to add enhanced profile fields to User model
# This should be added to db/user/migrations/

from django.db import migrations, models
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),  # Replace with the latest migration number
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='bio',
            field=models.TextField(
                blank=True,
                null=True,
                help_text="User's biography or personal description"
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='projects',
            field=models.JSONField(
                default=list,
                help_text="List of user's projects with title, link, description, and tags"
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='experience',
            field=models.JSONField(
                default=list,
                help_text="List of user's work experience with role, company, dates, and description"
            ),
        ),
    ]