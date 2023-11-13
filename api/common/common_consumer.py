import json

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Count
from django.db.models.functions import Coalesce

from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync

from db.learning_circle import LearningCircle
from db.learning_circle import UserCircleLink
from db.organization import Organization
from db.task import InterestGroup
from db.user import User, UserRoleLink

from utils.types import IntegrationType, OrganizationType


class GlobalCount(WebsocketConsumer):
    data = {}
    group_name = "landing_stats"

    def connect(self):
        async_to_sync(self.channel_layer.group_add)(
                self.group_name, 
                self.channel_name
            )
        self.accept()

        self.data = {
            'members': self.members_count,
            'org_type_counts': self.org_type_counts,
            'enablers_mentors_count': self.enablers_mentors_count,
            'ig_count': self.interest_groups_count,
            'learning_circle_count': self.learning_circles_count
        }

        self.send(text_data=json.dumps(self.data))
    
    def disconnect(self, code):
        self.channel_layer.group_discard(self.group_name, self.channel_name)

    @property
    def members_count(self):
        members_count = User.objects.all().count()
        return members_count
    
    @property
    def org_type_counts(self):
        org_type_counts = Organization.objects.filter(
                org_type__in=[OrganizationType.COLLEGE.value, OrganizationType.COMPANY.value,
                              OrganizationType.COMMUNITY.value]
            ).values('org_type').annotate(org_count=Coalesce(Count('org_type'), 0))
        org_type_counts = list(org_type_counts)

        return org_type_counts
    
    @property
    def enablers_mentors_count(self):
        enablers_mentors_count = UserRoleLink.objects.filter(
            role__title__in=["Mentor", "Enabler"]).values(
            'role__title').annotate(role_count=Coalesce(Count('role__title'), 0))
        enablers_mentors_count = list(enablers_mentors_count)

        return enablers_mentors_count
    
    @property
    def interest_groups_count(self):
        interest_groups_count = InterestGroup.objects.all().count()
        return interest_groups_count
    
    @property
    def learning_circles_count(self):
        learning_circles_count = LearningCircle.objects.all().count()
        return learning_circles_count
    
    def get_based_on_sender(self, sender):
        if sender == User:
            self.data['members'] = self.members_count

        elif sender == Organization:
            self.data['org_type_counts'] = self.org_type_counts

        elif sender == UserRoleLink:
            self.data['enablers_mentors_count'] = self.enablers_mentors_count

        elif sender == InterestGroup:
            self.data['ig_count'] = self.interest_groups_count

        elif sender == LearningCircle:
            self.data['learning_circle_count'] = self.learning_circles_count

    def receive(self, text_data):
        
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
            if created:
                self.get_based_on_sender(sender)
                async_to_sync(self.channel_layer.group_send)(
                    self.group_name,
                    {"type": "send_data", "data": self.data}
                )

            if created == None:
                self.get_based_on_sender(sender)
                async_to_sync(self.channel_layer.group_send)(
                    self.group_name,
                    {"type": "send_data", "data": self.data}
                )
    
    def send_data(self, event):
        self.send(text_data=json.dumps(event['data']))

    
