FROM python:3.10-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN mkdir /var/log/mulearnbackend
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev build-essential pkg-config \
 && rm -rf /var/lib/apt/lists/*
COPY ./requirements.txt .
RUN pip install -r requirements.txt
COPY . .
# EXPOSE 8000
# ENTRYPOINT sh entrypoint.sh
