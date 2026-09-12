"""Operation 12 (tasks/ROTA-T009/brief.md): backup and diagnostic ZIP.
Both stay behind the application boundary so a future UI never implements
storage/privacy logic itself. No cloud behavior, no telemetry/upload.

R4-11-B: actual SQL/table access lives in
rota.persistence.backup_repository -- this module is a thin wrapper only.

ROTA-RODO-ENCRYPTION-AT-REST (brief.md exact SHA 37620cf, section 4):
backup_database now composes a portable ZIP artifact (snapshot + format
manifest + a recoverable wrapped DEK representation, when one is
available) instead of returning a raw `.db` file, so recovering
Employee.display_name from a backup never depends on this installation's
runtime keystore surviving alongside it. create_local_recovery_kit and
recover_employee_names_from_backup are the backend recovery primitives
section 6 asks for -- no restore UI is built here.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
import zipfile
from datetime import date
from pathlib import Path

from rota.persistence import pii_crypto
from rota.persistence.backup_repository import backup_to, diagnostics_payload
from rota.persistence.employee_repository import decrypt_display_names_with_key
from rota.persistence.plan_preview_repository import get_plan_preview_with_key
from rota.persistence.site_memory import get_decision_required_snapshot_with_key

BACKUP_FORMAT_VERSION = 1


def backup_database(conn: sqlite3.Connection, destination: str, *, db_path: str) -> None:
    """db_path is the SOURCE database's own on-disk path (api/config.DB_PATH
    in production) -- needed to look up which runtime protector guards its
    DEK and, for LOCAL_WINDOWS, whether a recovery kit was ever created for
    it. Never embeds a plaintext DEK, a raw DPAPI blob, or the
    CENTRAL_SERVICE runtime secret itself (brief.md section 4/5.3)."""
    dek = pii_crypto.resolve_key(conn)
    protector_kind = pii_crypto.protector_kind_for(db_path)
    wrapped_dek: bytes | None = None
    if protector_kind == "CENTRAL":
        wrapped_dek = pii_crypto.wrap_dek_for_central_backup(dek)
    elif protector_kind == "DPAPI":
        sidecar = pii_crypto.recovery_sidecar_path(db_path)
        if not sidecar.exists():
            # R5-02: producing a backup with no recoverable DEK
            # representation would look identical to a real one until the
            # installation is actually lost -- refuse instead of handing
            # over a false sense of security (brief.md section 4).
            raise pii_crypto.RecoveryKitRequired(
                "no recovery kit exists yet for this database -- create one "
                "(\"Pobierz klucz odzyskiwania\") before the first backup, "
                "or this backup cannot be recovered after losing this computer"
            )
        wrapped_dek = sidecar.read_bytes()
    manifest = {
        "backup_format_version": BACKUP_FORMAT_VERSION,
        "protector_kind": protector_kind,
        "recovery_available": wrapped_dek is not None,
    }
    with tempfile.TemporaryDirectory() as tmp_dir:
        snapshot_path = Path(tmp_dir) / "snapshot.db"
        backup_to(conn, str(snapshot_path))
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot_path, "snapshot.db")
            archive.writestr("manifest.json", json.dumps(manifest))
            if wrapped_dek is not None:
                archive.writestr("wrapped_dek.bin", wrapped_dek)


def create_local_recovery_kit(conn: sqlite3.Connection, db_path: str) -> bytes:
    """LOCAL_WINDOWS only. Persists the wrapped-DEK recovery package next
    to db_path (safe -- it is ciphertext) so future backup_database() calls
    embed it automatically, and returns the raw recovery_key bytes for the
    caller to hand to the installation owner for separate safekeeping.
    Never persists that key anywhere itself -- section 5.1's requirement is
    that it lives somewhere other than this machine."""
    if pii_crypto.protector_kind_for(db_path) != "DPAPI":
        raise pii_crypto.KeyProtectionUnavailable(
            "a local recovery kit only applies to a LOCAL_WINDOWS (DPAPI-protected) database"
        )
    dek = pii_crypto.resolve_key(conn)
    package, recovery_key = pii_crypto.create_recovery_kit(dek)
    pii_crypto.recovery_sidecar_path(db_path).write_bytes(package)
    return recovery_key


def _recover_dek_and_open_snapshot(
    archive: zipfile.ZipFile, tmp_dir: str, *, recovery_key: bytes | None,
) -> tuple[bytes, sqlite3.Connection]:
    """Shared brief.md section 6 recovery step: unwrap the DEK using only
    the backup artifact (and, for LOCAL_WINDOWS, the independently-stored
    recovery_key) and open the extracted snapshot -- no original
    .pii_keystore, DPAPI context, or CENTRAL_SERVICE runtime process
    needs to be present, only ROTA_CENTRAL_KEK re-supplied in the
    environment for that model. Caller owns closing the connection."""
    try:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    except KeyError:
        raise pii_crypto.RecoveryFailed("not a recognized backup artifact: missing manifest.json") from None
    protector_kind = manifest.get("protector_kind")
    snapshot_path = Path(tmp_dir) / "snapshot.db"
    snapshot_path.write_bytes(archive.read("snapshot.db"))
    if protector_kind == "CENTRAL":
        dek = pii_crypto.unwrap_dek_from_central_backup(_read_zip_member(archive, "wrapped_dek.bin"))
    elif protector_kind == "DPAPI":
        if recovery_key is None:
            raise pii_crypto.RecoveryFailed("this backup requires its separately-stored recovery key")
        dek = pii_crypto.recover_dek_from_kit(_read_zip_member(archive, "wrapped_dek.bin"), recovery_key)
    else:
        raise pii_crypto.RecoveryFailed(f"unrecognized protector_kind in backup manifest: {protector_kind!r}")
    return dek, sqlite3.connect(snapshot_path)


def recover_employee_names_from_backup(zip_path: str, *, recovery_key: bytes | None = None) -> dict[str, str]:
    """Proves brief.md section 6's recovery primitive end to end: given
    only the backup ZIP (and, for a LOCAL_WINDOWS-protected one, the
    independently-stored recovery_key), reconstructs
    {employee_id: display_name} without the original .pii_keystore, DPAPI
    context, or CENTRAL_SERVICE runtime process needing to be present --
    only ROTA_CENTRAL_KEK re-supplied in the environment, for that model."""
    with zipfile.ZipFile(zip_path) as archive, tempfile.TemporaryDirectory() as tmp_dir:
        dek, snapshot_conn = _recover_dek_and_open_snapshot(archive, tmp_dir, recovery_key=recovery_key)
        try:
            return decrypt_display_names_with_key(snapshot_conn, dek)
        finally:
            snapshot_conn.close()


def recover_plan_preview_and_decision_snapshot_from_backup(
    zip_path: str, *, site_id: str, month: date, decision_required_id: str | None = None,
    recovery_key: bytes | None = None,
) -> tuple[list[str] | None, str | None]:
    """ROTA-RODO-DISPLAY-NAME-LEAKS-OUTSIDE-EMPLOYEES-TABLE brief.md
    section 6/L7: the same recovery primitive as
    recover_employee_names_from_backup, extended to prove
    plan_previews.warnings_json and decision_required_snapshots.
    payload_json decrypt with their correct record-bound AAD from the
    SAME recovered DEK -- no separate secret or backup format. Returns
    (warnings_for_site_month_or_None, decision_payload_text_or_None);
    decision_required_id may be omitted when only the preview half is
    being proven."""
    with zipfile.ZipFile(zip_path) as archive, tempfile.TemporaryDirectory() as tmp_dir:
        dek, snapshot_conn = _recover_dek_and_open_snapshot(archive, tmp_dir, recovery_key=recovery_key)
        try:
            preview = get_plan_preview_with_key(snapshot_conn, site_id, month, dek)
            warnings = list(preview.warnings) if preview is not None else None
            payload_text = None
            if decision_required_id is not None:
                snapshot = get_decision_required_snapshot_with_key(snapshot_conn, decision_required_id, dek)
                if snapshot is not None and snapshot.payload.unblocking_options:
                    payload_text = snapshot.payload.unblocking_options[0].text
            return warnings, payload_text
        finally:
            snapshot_conn.close()


def _read_zip_member(archive: zipfile.ZipFile, name: str) -> bytes:
    try:
        return archive.read(name)
    except KeyError:
        raise pii_crypto.RecoveryFailed(f"backup artifact has no recovery material available ({name} missing)") from None


def build_diagnostic_zip(
    conn: sqlite3.Connection,
    destination: str,
    *,
    frontend_report: dict | None = None,
    runtime_log_dir: Path | str | None = None,
) -> None:
    """ROTA-TECHNICAL-ERROR-RECOVERY-UX (brief.md section 5): embeds the
    current runtime-errors.log plus any of its rotated copies, when they
    exist -- resolving WHERE they live is a deployment-model concern the
    caller (api layer) already owns via api.runtime_log, never this
    application-layer module. A missing/absent log is not an error: the
    ZIP is produced exactly as before."""
    payload = diagnostics_payload(conn)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("diagnostics.json", json.dumps(payload, indent=2))
        if frontend_report is not None:
            archive.writestr("frontend_diagnostics.json", json.dumps(frontend_report, indent=2))
        if runtime_log_dir is not None:
            log_dir = Path(runtime_log_dir)
            for log_file in sorted(log_dir.glob("runtime-errors.log*")):
                archive.write(log_file, f"logs/{log_file.name}")
