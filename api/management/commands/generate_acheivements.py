from django.core.management.base import BaseCommand
from typing import Any, Optional
from db.achievement import Achievement, UserAchievementsLog
from django.conf import settings

from db.user import User


class Command(BaseCommand):

    help = "Comamnd to generate achievements for users"

    def add_arguments(self, parser):
        pass

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        users = User.objects.select_related("user_lvl_link_user__level").filter()
        levels = {}

        for i in range(1, 8):
            levels[i] = Achievement.objects.filter(level_id__level_order=i).first()
        i = 0
        print("started generating achievements")

        for user in users:
            i += 1
            if i % 100 == 0:
                print("Processed users: ", i)
            try:
                level_link = user.user_lvl_link_user
            except:
                continue
            if not level_link:
                continue
            level = level_link.level
            level_order = level.level_order

            batch = []

            for i in range(1, level_order + 1):
                achievement = levels.get(i)
                if not achievement:
                    continue
                if UserAchievementsLog.objects.filter(
                    user_id=user, achievement_id=achievement
                ).exists():
                    continue
                batch.append(
                    UserAchievementsLog(
                        user_id=user,
                        achievement_id=achievement,
                        created_by_id=settings.SYSTEM_ADMIN_ID,
                        updated_by_id=settings.SYSTEM_ADMIN_ID,
                    )
                )
            UserAchievementsLog.objects.bulk_create(batch)
            print("added user acheivements for users")
