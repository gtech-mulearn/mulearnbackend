# Mulearn Backend Project

## Setup

1) Clone the project.
2) Create a virtual environment in 'venv' folder and activate it.
3) Install the dependencies with
    ```commandline
    Pip install -r requirements.txt
    ```

4) Create .env file with following properties--
    ```markdown
    SECRET_KEY=
    DEBUG=

    DATABASE_ENGINE=
    DATABASE_USER=
    DATABASE_PASSWORD=
    DATABASE_NAME=
    DATABASE_HOST=
    DATABASE_PORT=
    ```

5) Add your actual values to .env file
6) Now create the migrations
   ```commandline
   python manage.py makemigrations
   python manage.py migrate
   ```
7) Now run the project
   ```commandline
   python manage.py runserver
   ```
