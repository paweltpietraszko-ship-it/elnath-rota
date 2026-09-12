"""ROTA-TECHNICAL-ERROR-RECOVERY-UX (brief.md exact SHA fe689a1, sections
3-4): the ONE sanitized runtime error log for the whole application. This
is not a telemetry/SIEM/activity-log system -- it exists so CC has a
technical trace after a real failure instead of asking the owner to
describe/screenshot what they saw.

Entries are built ONLY from the explicitly allowed fields the brief lists
(timestamp, severity, component, exception type, a fixed safe message,
stack trace when a real exception exists, incident_id). No automatic
redaction engine (brief section 3, last line) -- callers never pass
display_name, form content, request/response bodies, absence/decision
data, secrets, or a raw PlanningResult.error_message; they pass a fixed,
already-safe sentence instead.
"""
from __future__ import annotations

import logging
import os
import secrets
import traceback
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from api.config import DB_PATH
from rota.persistence.pii_crypto import CENTRAL_KEK_ENV_VAR

LOG_FILENAME = "runtime-errors.log"
LOG_DIR_ENV_VAR = "ROTA_LOG_DIR"
_MAX_BYTES = 1 * 1024 * 1024
_BACKUP_COUNT = 4

_logger: logging.Logger | None = None


class RuntimeLogConfigurationError(RuntimeError):
    """brief.md section 4/A10: CENTRAL_SERVICE requires ROTA_LOG_DIR --
    a missing required persistent location is a deployment config error,
    never a silent fallback to some other, unknown place."""


def resolve_log_dir() -> Path:
    """CENTRAL_SERVICE is detected the same way pii_crypto already does
    (ROTA_CENTRAL_KEK presence) -- reusing that existing signal instead of
    inventing a second deployment-model marker."""
    configured = os.environ.get(LOG_DIR_ENV_VAR)
    if os.environ.get(CENTRAL_KEK_ENV_VAR):
        if not configured:
            raise RuntimeLogConfigurationError(
                f"CENTRAL_SERVICE requires {LOG_DIR_ENV_VAR} to be set for the runtime error log"
            )
        return Path(configured)
    if configured:
        return Path(configured)
    # LOCAL_WINDOWS default (brief section 4): next to the application's
    # own database file, in a logs/ subdirectory -- same convention
    # rota.persistence.pii_crypto already uses for its own sidecar files.
    return Path(DB_PATH).resolve().parent / "logs"


def reset_for_tests() -> None:
    """Test-only: drop the cached logger/handler so a changed ROTA_LOG_DIR
    or ROTA_CENTRAL_KEK takes effect on the next log_runtime_error call,
    and release the file handle so a temp directory can be cleaned up."""
    global _logger
    if _logger is not None:
        for handler in list(_logger.handlers):
            handler.close()
            _logger.removeHandler(handler)
    _logger = None


def _get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger
    log_dir = resolve_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("rota.runtime_errors")
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    handler = RotatingFileHandler(
        log_dir / LOG_FILENAME, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    _logger = logger
    return logger


def log_runtime_error(
    *, component: str, safe_message: str, severity: str = "ERROR",
    exc: BaseException | None = None, exception_type: str | None = None,
) -> str:
    """Writes exactly one sanitized entry and returns its incident_id.

    `safe_message` must already be a fixed, non-domain-content sentence.
    `exc`, when given, contributes its exception type name and full
    traceback (brief section 3: a real stack trace for a genuinely
    unhandled exception is the whole point of this log; the brief's
    "no automatic redaction engine" line means this traceback is not
    scrubbed further -- callers with a structured, exception-less
    TECHNICAL_ERROR pass `exception_type` instead, e.g.
    "STRUCTURED_PLANNING_FAILURE", and never pass exc)."""
    incident_id = secrets.token_hex(8)
    timestamp = datetime.now(timezone.utc).isoformat()
    resolved_type = exception_type or (type(exc).__name__ if exc is not None else "UNKNOWN")
    line = f"{timestamp} {severity} [{component}] incident={incident_id} type={resolved_type}: {safe_message}"
    if exc is not None:
        stack = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).rstrip("\n")
        line += "\n" + stack
    logger = _get_logger()
    level = getattr(logging, severity, logging.ERROR)
    logger.log(level, line)
    return incident_id
