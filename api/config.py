"""ROTA-T021 brief.md section 3.3: interim coordinator_id, pending real
login (F1). A single dev-config value, never a UI control. Deleted
outright, not extended, once real authentication exists.

ROTA-T024-TESTER-LOGIN-ISOLATION (brief.md exact SHA 9246fad, section 11):
"Ten kontrakt dotyczy hostowanego deploymentu" -- login/per-account
isolation applies only to CENTRAL_SERVICE (a shared Railway deployment
with multiple testers). LOCAL_WINDOWS is one desktop, one owner -- there
is no one else to isolate from, so it keeps today's DEV_COORDINATOR_ID/
DB_PATH behavior unchanged (brief section 9's explicit LOCAL_WINDOWS
carve-out). IS_CENTRAL_SERVICE reuses the same deployment-model signal
pii_crypto/runtime_log already use, rather than a second marker.
"""
from __future__ import annotations

import os
from pathlib import Path

from rota.persistence.pii_crypto import CENTRAL_KEK_ENV_VAR

DEV_COORDINATOR_ID = os.environ.get("ROTA_DEV_COORDINATOR_ID", "DEV-COORD-1")
DB_PATH = os.environ.get("ROTA_DB_PATH", "rota_dev.db")

IS_CENTRAL_SERVICE = bool(os.environ.get(CENTRAL_KEK_ENV_VAR))

# ROTA-T024: only meaningful when IS_CENTRAL_SERVICE. The small, separate
# SQLite holding fastapi-users' own tables plus Rota's own account->
# coordinator/database mapping table (brief section 5: never mixed with
# a tester's own domain database).
AUTH_DB_PATH = os.environ.get("ROTA_AUTH_DB_PATH", "rota_auth.db")

# The one trusted directory per-tester domain databases may live in --
# brief section 5: "db_filename -- tylko nazwa pliku w zaufanym katalogu,
# nie dowolna ścieżka". Never accept a caller-supplied absolute path.
ACCOUNTS_DB_DIR = Path(os.environ.get("ROTA_ACCOUNTS_DB_DIR", "accounts"))

# Secret fastapi-users uses to sign JWT session tokens / password-reset
# and verification tokens (the latter two routers are never mounted --
# brief section 3 -- but BaseUserManager still requires the attribute).
# No safe default: a real CENTRAL_SERVICE deployment must set this.
AUTH_SECRET = os.environ.get("ROTA_AUTH_SECRET", "")
