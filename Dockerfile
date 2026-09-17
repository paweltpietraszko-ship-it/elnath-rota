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
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app

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
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
# Railway injects PORT at runtime; -m ensures the repo root (this
# directory) is on sys.path so `api`/`rota` resolve without installation.
CMD ["sh", "-c", "python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
