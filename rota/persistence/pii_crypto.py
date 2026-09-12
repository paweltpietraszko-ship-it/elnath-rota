"""ROTA-RODO-ENCRYPTION-AT-REST (technical demo, field-level variant):
encrypts Employee.display_name at rest, decrypts transparently on read.

Pattern adapted from LynxMask-Desktop's anonymizer_crypto.py: AES-256-GCM
with a random key protected by Windows DPAPI (file-permission fallback on
other platforms). Narrower than the whole-database (SQLCipher) approach
tried first for this same finding: only the one column that actually
carries a person's name is ciphertext, the surrounding SQLite file stays
an ordinary, freely-openable database. This avoids both problems that
approach ran into -- no foreign exception-class hierarchy for existing
`except sqlite3.Error`/`pytest.raises(sqlite3.Error)` call sites to trip
over (still plain stdlib sqlite3 throughout), and no "the whole file
won't open" break for a database that predates this change, since a row
written before encryption existed is still an ordinary, readable string
in the very same TEXT column -- decrypt_name() below falls back to
returning it unchanged instead of raising.

Employee.employee_id is the identity every other table, rule and solver
decision actually joins/reasons on (grepped: no other file in rota/
selects or filters on employees.display_name in SQL); display_name is
purely a human-readable label read back out at the repository boundary
for display/print, so decrypting immediately on read (rather than
threading an encrypted wrapper type through solver.py/schedule_export.py/
the API layer) is not a scope reduction -- there is no business logic
downstream that would ever benefit from staying encrypted in memory.
"""
from __future__ import annotations

import os
import platform
import secrets
import sqlite3
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_SIZE = 32
NONCE_SIZE = 12
MAGIC = b"RNAM\x01"  # distinguishes an encrypted value from legacy plaintext
KEYSTORE_SUFFIX = ".pii_keystore"

# Keyed by the real file path (a stable, safe identity -- unlike id(conn),
# which sqlite3.Connection objects reuse after garbage collection: a first
# version of this cache keyed by id(conn) caused several full-suite tests
# to fail with a wrong-key IntegrityError, because a new connection to a
# DIFFERENT database could reuse the numeric id of an old, already-closed
# connection to a different one). sqlite3.Connection supports neither
# weakref nor arbitrary attributes, so there is no safe way to cache
# anything keyed by connection identity at all -- only by the real path.
_key_cache_by_path: dict[str, bytes] = {}

# :memory: has no file, so no path to key a persistent cache on. Since a
# :memory: database is never written to disk, "at rest" protection is
# moot for it anyway (see decrypt_name's module docstring on this same
# point) -- a single random key shared by every :memory: connection in
# this process keeps write-then-read correct within and across such
# connections without needing any per-connection bookkeeping at all.
_MEMORY_KEY = secrets.token_bytes(KEY_SIZE)


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _dpapi_protect(data: bytes) -> bytes:
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = DATA_BLOB(len(data), buf)
    blob_out = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out),
    )
    if not ok:
        raise RuntimeError(f"DPAPI CryptProtectData failed: {ctypes.GetLastError()}")
    result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return result


def _dpapi_unprotect(data: bytes) -> bytes:
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = DATA_BLOB(len(data), buf)
    blob_out = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out),
    )
    if not ok:
        raise RuntimeError(f"DPAPI CryptUnprotectData failed: {ctypes.GetLastError()}")
    result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return result


def _keystore_path(db_path: Path) -> Path:
    return db_path.with_name(db_path.name + KEYSTORE_SUFFIX)


def _get_or_create_key_for_path(db_path: Path) -> bytes:
    ks_path = _keystore_path(db_path)
    if ks_path.exists():
        protected = ks_path.read_bytes()
        return _dpapi_unprotect(protected) if _is_windows() else protected

    key = secrets.token_bytes(KEY_SIZE)
    protected = _dpapi_protect(key) if _is_windows() else key
    ks_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = ks_path.with_suffix(ks_path.suffix + ".tmp")
    tmp.write_bytes(protected)
    if not _is_windows():
        os.chmod(tmp, 0o600)
    tmp.replace(ks_path)
    return key


def _main_db_file(conn: sqlite3.Connection) -> str:
    """Empty string for :memory: / a temporary on-disk database, per
    PRAGMA database_list's own documented convention."""
    for _seq, name, file in conn.execute("PRAGMA database_list").fetchall():
        if name == "main":
            return file
    return ""


def resolve_key(conn: sqlite3.Connection) -> bytes:
    """Callers resolve this ONCE per repository-level call (get_employee,
    list_employees, ...) and pass the result down to encrypt_name/
    decrypt_name for every row -- never once per row. PRAGMA database_list
    is a real executed SQL statement; calling it per row breaks the exact
    query-count guarantee tests/test_t019.py::test_23_n_plus_1_oracle
    enforces (caught on the first pass of this design: 13 queries for 8
    employees vs. 6 for 1)."""
    path = _main_db_file(conn)
    if not path:
        return _MEMORY_KEY
    if path not in _key_cache_by_path:
        _key_cache_by_path[path] = _get_or_create_key_for_path(Path(path))
    return _key_cache_by_path[path]


def encrypt_name(key: bytes, plaintext: str) -> bytes:
    nonce = secrets.token_bytes(NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return MAGIC + nonce + ciphertext


def decrypt_name(key: bytes, stored: bytes | str) -> str:
    """A row written before this feature existed still holds a plain
    string (or already-plain `bytes` from Python's own str/bytes sqlite3
    round-trip) with no MAGIC header -- returned unchanged rather than
    raising, so an existing database keeps working exactly as before."""
    if isinstance(stored, str):
        return stored
    if not stored.startswith(MAGIC):
        return stored.decode("utf-8", errors="replace")
    blob = stored[len(MAGIC):]
    nonce, ciphertext = blob[:NONCE_SIZE], blob[NONCE_SIZE:]
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, None).decode("utf-8")
    except InvalidTag:
        raise ValueError("employee display_name failed integrity check -- possibly corrupted or tampered")
