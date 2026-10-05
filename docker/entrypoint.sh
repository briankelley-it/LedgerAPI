#!/bin/sh
# Apply database migrations, then run whatever command was given (gunicorn by default).
set -e

python manage.py migrate --noinput

exec "$@"
