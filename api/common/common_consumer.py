import json

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Count
from django.db.models.functions import Coalesce

from db.learning_circle import LearningCircle
from db.learning_circle import UserCircleLink
from db.organization import Organization
from db.task import InterestGroup
from db.user import User, UserRoleLink

from utils.types import IntegrationType, OrganizationType
from utils.baseconsumer import BaseConsumer


class GlobalCount(BaseConsumer):

    def receive(self, text_data):
        if json.loads(text_data)['type'] == 'global_count':
            org_type_counts = Organization.objects.filter(
                org_type__in=[OrganizationType.COLLEGE.value, OrganizationType.COMPANY.value,
                              OrganizationType.COMMUNITY.value]
            ).values('org_type').annotate(org_count=Coalesce(Count('org_type'), 0))
            org_type_counts = list(org_type_counts)

            enablers_mentors_count = UserRoleLink.objects.filter(
                role__title__in=["Mentor", "Enabler"]).values(
                'role__title').annotate(role_count=Coalesce(Count('role__title'), 0))
            enablers_mentors_count = list(enablers_mentors_count)

            interest_groups_count = InterestGroup.objects.all().count()
            learning_circles_count = LearningCircle.objects.all().count()
            members_count = User.objects.all().count()

            data = {
                'members': members_count,
                'org_type_counts': org_type_counts,
                'enablers_mentors_count': enablers_mentors_count,
                'ig_count': interest_groups_count,
                'learning_circle_count': learning_circles_count
            }

            self.send(text_data=json.dumps(data))

        @receiver(post_save, sender=User)
        @receiver(post_save, sender=LearningCircle)
        @receiver(post_save, sender=InterestGroup)
        def user_post_save(sender, instance, created, **kwargs):
            data = {}

            if created:
                if sender == User:
                    count = User.objects.all().count()
                    data['members'] = count
                elif sender == LearningCircle:
                    count = LearningCircle.objects.all().count()
                    data['learning_circle_count'] = count
                elif sender == InterestGroup:
                    count = InterestGroup.objects.all().count()
                    data['ig_count'] = count

                self.send(text_data=json.dumps(data))

        @receiver(post_delete, sender=User)
        @receiver(post_delete, sender=LearningCircle)
        @receiver(post_delete, sender=InterestGroup)
        def user_post_delete(sender, instance, created, **kwargs):
            data = {}

            if sender == User:
                count = User.objects.all().count()
                data['members'] = count
            elif sender == LearningCircle:
                count = LearningCircle.objects.all().count()
                data['learning_circle_count'] = count
            elif sender == InterestGroup:
                count = InterestGroup.objects.all().count()
                data['ig_count'] = count

            self.send(text_data=json.dumps(data))
