# Recipe for the backend container (Python + Django). Two targets: "dev" (default, your PC) and "production".
# ASK FIRST before changing this file.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System libraries for PDF printing (WeasyPrint) and Noto fonts for Gujarati / Hindi on documents
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# ---------------------------------------------------------------------------
# PRODUCTION image (a real server). Used by docker-compose.prod.yml  (target: production)
# Runs as a normal user (not root), with gunicorn instead of the development server.
# ---------------------------------------------------------------------------
FROM base AS production
RUN useradd --create-home --uid 1000 app     && mkdir -p /app/staticfiles /app/media /app/private_media     && chown -R app:app /app
COPY --chown=app:app . /app
USER app
EXPOSE 8000

# ---------------------------------------------------------------------------
# DEVELOPMENT image (your PC). This is the LAST stage, so plain "docker compose up" uses it.
# ---------------------------------------------------------------------------
FROM base AS dev
COPY . /app
EXPOSE 8000
