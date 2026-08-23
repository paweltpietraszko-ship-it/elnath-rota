"""ROTA-T021 brief.md section 3.3: interim coordinator_id, pending real
login (F1). A single dev-config value, never a UI control. Deleted
outright, not extended, once real authentication exists.
"""
from __future__ import annotations

import os

DEV_COORDINATOR_ID = os.environ.get("ROTA_DEV_COORDINATOR_ID", "DEV-COORD-1")
DB_PATH = os.environ.get("ROTA_DB_PATH", "rota_dev.db")
