#!/bin/sh
set -e

echo "[entrypoint] Waiting for MySQL..."
until python - <<'PY'
import os
import MySQLdb

MySQLdb.connect(
    host=os.environ.get("DJANGO_DB_HOST", "db"),
    user=os.environ.get("DJANGO_DB_USER", "root"),
    passwd=os.environ.get("DJANGO_DB_PASSWORD", "88226858"),
    port=int(os.environ.get("DJANGO_DB_PORT", "3306")),
    db=os.environ.get("DJANGO_DB_NAME", "__django_app_db__"),
)
PY
do
  sleep 2
done

echo "[entrypoint] Waiting for Redis..."
until python - <<'PY'
import os
import socket

host = os.environ.get("REDIS_HOST", "redis")
port = int(os.environ.get("REDIS_PORT", "6379"))
with socket.create_connection((host, port), timeout=2):
    pass
PY
do
  sleep 1
done

echo "[entrypoint] Running migrations..."
python manage.py migrate --noinput

case "$1" in
  web)
    echo "[entrypoint] Starting Django (0.0.0.0:8000)..."
    exec python manage.py runserver 0.0.0.0:8000
    ;;
  worker)
    echo "[entrypoint] Starting RQ worker..."
    exec python manage.py rqworker default
    ;;
  *)
    exec "$@"
    ;;
esac
