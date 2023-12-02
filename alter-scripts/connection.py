import pymysql
from decouple import config

db_config = {
    'host': config('DATABASE_HOST'),
    'user': config('DATABASE_USER'),
    'password': config('DATABASE_PASSWORD'),
    'db': config('DATABASE_NAME'),
}


def execute(query):
    with pymysql.connect(**db_config) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()
