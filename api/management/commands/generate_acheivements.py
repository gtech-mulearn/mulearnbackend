from django.core.management.base import BaseCommand
from typing import Any, Optional
from db.achievement import Achievement, UserAchievements

from db.user import User


class Command(BaseCommand):

    help = "Comamnd to generate achievements for users"

    def add_arguments(self, parser):
        pass

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        users = User.objects.select_related("user_lvl_link_user__level").filter()
        levels = {}

        for i in range(1, 7):
            levels[i] = Achievement.objects.get(level__level_order=i)

        for user in users:
            try:
                level_link = user.user_lvl_link_user
            except:
                continue
            if not level_link:
                continue
            level = level_link.level
            level_order = level.level_order
            for i in range(1, level_order + 1):
                achievement = levels[i]
                UserAchievements.objects.create(
                    user_id=user, achievement_id=achievement
                )
            print(
                "Achievements generated for user: ", user.muid, "Level: ", level_order
            )
