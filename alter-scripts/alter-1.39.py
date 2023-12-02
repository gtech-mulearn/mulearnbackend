import os
import requests
from io import BytesIO
from os.path import splitext
from django.core.files.storage import FileSystemStorage
import django
import sys
from connection import execute

os.chdir('..')
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mulearnbackend.settings')
django.setup()


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
    data = execute("SELECT id, profile_pic FROM user WHERE profile_pic IS NOT NULL;")
    for user_id, profile_pic in data:
        save_image(user_id, profile_pic)

    execute("UPDATE system_setting SET value = '1.39', updated_at = now() WHERE `key` = 'db.version';")
