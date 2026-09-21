# ROTA-RAILWAY-DEPLOY: one container serves both the API and the built
# frontend (api/main.py mounts frontend/dist as static files when present).
# Railway auto-detects this file and builds/deploys it as a single service.

FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# ROTA-T024-TESTER-LOGIN-ISOLATION: build-time flag that turns on the
# login screen -- must be set here, not left to a runtime toggle a
# viewer could flip (frontend/vite.config.ts).
ENV ROTA_CENTRAL_SERVICE=1
# Codex R1-02 finding on 6b84a34: .git is excluded from the build context
# (.dockerignore), so `git rev-parse` inside this stage always failed and
# every production bundle silently baked in build_sha="unknown". Railway
# auto-populates this ARG with the real commit SHA for Dockerfile deploys;
# a plain local `docker build` with no --build-arg falls back to "unknown"
# same as before (still correct there -- it isn't a Railway build).
ARG RAILWAY_GIT_COMMIT_SHA=""
ENV ROTA_BUILD_SHA=$RAILWAY_GIT_COMMIT_SHA
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app

# ROTA-RAILWAY-PDF-MISSING-POLISH-FONT: python:3.12-slim ships with zero
# TrueType fonts. schedule_export.py's font resolution (_font_candidates)
# looks for /usr/share/fonts/truetype/dejavu/DejaVuSans*.ttf on Linux --
# without it, every code path falls through to reportlab's bundled Vera
# font, which has no Polish diacritics, and every PDF export here fails
# closed with PRINT_FONT_UNAVAILABLE. fonts-dejavu-core installs to
# exactly that path with full Polish glyph coverage.
RUN apt-get update && apt-get install --no-install-recommends -y fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Dependency list mirrors [project.dependencies] in pyproject.toml exactly
# -- keep both in sync by hand. Not installed via `pip install .`: rota/
# is an implicit namespace package (no __init__.py), so this project runs
# unpackaged everywhere, dev and here alike (PYTHONPATH = repo root).
RUN pip install --no-cache-dir \
    "ortools>=9.0" "reportlab==5.0.1" "fastapi>=0.135" "uvicorn>=0.44" \
    "hypothesis>=6.100" "holidays>=0.60" "cryptography>=42" \
    "fastapi-users[sqlalchemy]==15.0.5" "fastapi-users-db-sqlalchemy==7.0.0" \
    "SQLAlchemy==2.0.52" "aiosqlite==0.22.1"

COPY api ./api
COPY rota ./rota
COPY excel ./excel
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
# Railway injects PORT at runtime; -m ensures the repo root (this
# directory) is on sys.path so `api`/`rota` resolve without installation.
CMD ["sh", "-c", "python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
