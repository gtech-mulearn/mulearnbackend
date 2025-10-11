import json

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from channels.generic.websocket import WebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from db.learning_circle import LearningCircle
from db.learning_circle import UserCircleLink
from db.organization import Organization
from db.task import InterestGroup, KarmaActivityLog
from db.user import User, UserRoleLink

from utils.types import IntegrationType, OrganizationType

class LandingStats:
    data = {}

    def members_count(self):
        members_count = User.objects.all().count()
        return members_count

    def org_type_counts(self):
        org_type_counts = Organization.objects.filter(
                org_type__in=[OrganizationType.COLLEGE.value, OrganizationType.COMPANY.value,
                                OrganizationType.COMMUNITY.value]
            ).values('org_type').annotate(org_count=Coalesce(Count('org_type'), 0))
        org_type_counts = list(org_type_counts)

        return org_type_counts

    def enablers_mentors_count(self):
        enablers_mentors_count = UserRoleLink.objects.filter(
            role__title__in=["Mentor", "Enabler"]).values(
            'role__title').annotate(role_count=Coalesce(Count('role__title'), 0))
        enablers_mentors_count = list(enablers_mentors_count)

        return enablers_mentors_count

    def interest_groups_count(self):
        interest_groups_count = InterestGroup.objects.all().count()
        return interest_groups_count

    def learning_circles_count(self):
        learning_circles_count = LearningCircle.objects.all().count()
        return learning_circles_count
    
    def karma_pow_count(self):
        karma_pow_count = KarmaActivityLog.objects.aggregate(karma_count=Coalesce(Sum('karma'), 0), pow_count=Count('id'))
        return karma_pow_count

    def get_data(self, sender):
        if sender == None:
            self.data = {
                'members': self.members_count(),
                'org_type_counts': self.org_type_counts(),
                'enablers_mentors_count': self.enablers_mentors_count(),
                'ig_count': self.interest_groups_count(),
                'learning_circle_count': self.learning_circles_count(),
                'karma_pow_count': self.karma_pow_count()
            }
        elif sender == User:
            self.data['members'] = self.members_count()

        elif sender == Organization:
            self.data['org_type_counts'] = self.org_type_counts()

        elif sender == UserRoleLink:
            self.data['enablers_mentors_count'] = self.enablers_mentors_count()

        elif sender == InterestGroup:
            self.data['ig_count'] = self.interest_groups_count()

        elif sender == LearningCircle:
            self.data['learning_circle_count'] = self.learning_circles_count()


landing_stats = LandingStats()

class GlobalCount(WebsocketConsumer):
    data = {}
    group_name = "landing_stats"

    def connect(self):
        async_to_sync(self.channel_layer.group_add)(
                self.group_name, 
                self.channel_name
            )
        self.accept()

        landing_stats.get_data(None)
        self.data = landing_stats.data

        self.send(text_data=json.dumps(self.data))
    
    def disconnect(self, code):
        self.channel_layer.group_discard(self.group_name, self.channel_name)
    
    def send_data(self, event):
        self.send(text_data=json.dumps(event['data']))

channel_layer = get_channel_layer()
    
@receiver(post_save, sender=User)
@receiver(post_save, sender=LearningCircle)
@receiver(post_save, sender=InterestGroup)
@receiver(post_save, sender=UserRoleLink)
@receiver(post_save, sender=Organization)
@receiver(post_delete, sender=User)
@receiver(post_delete, sender=LearningCircle)
@receiver(post_delete, sender=InterestGroup)
@receiver(post_delete, sender=UserRoleLink)
@receiver(post_delete, sender=Organization)
def db_signals(sender, instance, created=None, *args, **kwargs):
    if created or created == None:
        landing_stats.get_data(sender)
        data = landing_stats.data
        async_to_sync(channel_layer.group_send)(
            "landing_stats",
            {"type": "send_data", "data": data}
        )
