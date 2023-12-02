import os
import pymysql
import requests
from io import BytesIO
from os.path import splitext
from django.core.files.storage import FileSystemStorage
from decouple import config
import django
import sys

sys.path.insert(0, 'path_to_mulearnbackend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mulearnbackend.settings')
django.setup()


def fetch_data(connection, query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall()


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
    db_config = {
        'host': config('DATABASE_HOST'),
        'user': config('DATABASE_USER'),
        'password': config('DATABASE_PASSWORD'),
        'db': config('DATABASE_NAME'),
    }

    with pymysql.connect(**db_config) as connection:
        data = fetch_data(connection, "SELECT id, profile_pic FROM user WHERE profile_pic IS NOT NULL;")
        for user_id, profile_pic in data:
            img = save_image(user_id, profile_pic)
