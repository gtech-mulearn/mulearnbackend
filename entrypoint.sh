#!/bin/bash
python manage.py collectstatic --noinput
gunicorn --bind 0.0.0.0:8000 mulearnbackend.wsgi
