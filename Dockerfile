FROM python:3.10-slim-buster
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN mkdir /var/log/mulearnbackend
RUN apt-get update -y  && apt-get install -y default-libmysqlclient-dev python-dev && apt install build-essential -y
# Every package pinned and hash-checked (issue 0039). Regenerate the lock after changing requirements.txt.
COPY ./requirements.lock .
# The base image's pip (23.0.1) rejects a dependency with extras (twisted[tls]) in hash mode.
RUN pip install pip==25.1.1 && pip install --require-hashes -r requirements.lock
COPY . .
# EXPOSE 8000
# ENTRYPOINT sh entrypoint.sh
