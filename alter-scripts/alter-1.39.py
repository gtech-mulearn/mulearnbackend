import os
import requests
from io import BytesIO
from os.path import splitext
from django.core.files.storage import FileSystemStorage
import django
import sys

os.chdir('..')
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mulearnbackend.settings')
django.setup()

from db.user import User
from db.settings import SystemSetting


def save_image(user_id, url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        extension = splitext(url)[-1].split("?")[0]
        pic = BytesIO(response.content)
        fs = FileSystemStorage()
        filename = f"user/profile/{user_id}{extension}"
        return fs.save(filename, pic)
    except Exception as e:
        print(e)


if __name__ == "__main__":
    users = User.objects.filter(profile_pic__isnull=False)
    for user in users:
        save_image(user.id, user.profile_pic)

    settings = SystemSetting.objects.filter(key="db.version").first()
    settings.value = "1.39"
    settings.save()
