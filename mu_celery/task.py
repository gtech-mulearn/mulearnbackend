from celery import shared_task
from utils.utils import send_template_mail
import requests
from decouple import config
from db.user import User

DISCORD_GUILD_ID = config("DISCORD_GUILD_ID")
DISCORD_BOT_TOKEN = config("DISCORD_BOT_TOKEN")


@shared_task
def send_email(context: dict, subject: str, address: list[str], attachment: str = None):
    return send_template_mail(context, subject, address, attachment)


@shared_task
def onboard_user(access_token: str, user_id: int):
    user = User.objects.get(id=user_id)
    user_response = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if user_response.status_code != 200:
        return {"status": "error", "message": "Failed to get user data"}
    user_data = user_response.json()
    discord_user_id = user_data.get("id")
    guild_url = (
        f"https://discord.com/api/guilds/{DISCORD_GUILD_ID}/members/{discord_user_id}"
    )
    member_data = {"access_token": access_token}
    bot_headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    already_linked_account = User.objects.filter(discord_id=discord_user_id).first()
    if already_linked_account:
        already_linked_account.exist_in_guild = False
        already_linked_account.discord_id = None
        already_linked_account.save()
    user.discord_id = discord_user_id
    user.exist_in_guild = True
    user.save()
    join_response = requests.put(guild_url, json=member_data, headers=bot_headers)
    if (
        join_response.status_code != 201
        and join_response.status_code != 200
        and join_response.status_code != 204
    ):
        return {"status": "error", "message": "Failed to join guild"}
    return {"status": "success", "message": "User onboarded successfully"}
