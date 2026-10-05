# syntax=docker/dockerfile:1

# ---- prod: what actually runs the API ----
FROM python:3.12-slim AS prod

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Collect admin CSS/JS at build time. The key is only used for this command.
RUN SECRET_KEY=build-only python manage.py collectstatic --noinput

# Run as a normal user, not root.
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/')"

ENTRYPOINT ["./docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]

# ---- dev: prod plus test and lint tools ----
FROM prod AS dev
USER root
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
USER appuser
