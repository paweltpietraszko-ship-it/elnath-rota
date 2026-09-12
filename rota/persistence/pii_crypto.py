"""ROTA-RODO-ENCRYPTION-AT-REST -- encrypts Employee.display_name at rest.

brief.md (exact SHA 37620cf) separates three responsibilities that the
first field-level pass (da1982e) conflated:

1. Data Encryption Key (DEK) -- one random 256-bit AES-GCM key per
   database, never derived from path/machine/account/password.
2. Runtime Key Protector -- how the DEK is protected for everyday use.
   Exactly two supported deployment models, chosen by whether
   ROTA_CENTRAL_KEK is configured, never a silent third fallback:
   - LOCAL_WINDOWS: DEK wrapped by Windows DPAPI, persisted in a
     `<db>.pii_keystore` sidecar. DPAPI ties it to this Windows account
     on this machine -- fine for daily use, useless after losing either.
   - CENTRAL_SERVICE: DEK wrapped by a KEK supplied by the deployment
     environment (ROTA_CENTRAL_KEK, 64 hex chars = 32 bytes), never
     written to disk itself. Missing/wrong KEK fails closed -- this
     module never generates a replacement DEK to paper over that.
3. Recovery -- independent of the runtime protector, so losing the
   Windows profile/DPAPI context (or a user's own login/password, which
   is not the DEK and never was) does not by itself destroy access to
   already-encrypted data, provided the independent recovery material
   was actually kept:
   - LOCAL_WINDOWS: create_recovery_kit() wraps the DEK with a freshly
     generated, one-time recovery key that this module never persists --
     the caller (rota/application/backup.py) is responsible for handing
     that key to the installation owner for safekeeping AWAY from this
     machine, separately from the recovery package itself.
   - CENTRAL_SERVICE: recovery reuses the same externally-supplied KEK
     mechanism as runtime protection -- the deployment's own management
     of that secret IS the recovery capability; this module does not
     implement a second, competing one.

Employee.employee_id remains the identity everything else in rota/
joins/reasons on (grepped: no other query selects or filters on
employees.display_name); display_name is decrypted immediately at the
repository boundary (resolve_key + decrypt_name in employee_repository.py)
since nothing downstream would benefit from an encrypted value in memory.

Ciphertext format (encrypt_name/decrypt_name): MAGIC + FORMAT_VERSION are
bound into the AEAD associated data, so tampering with either changes
what the GCM tag was computed over -- corruption or a deliberate
downgrade attempt both fail the same authenticated way, never silently
falling through to plaintext decoding. A `str` value is trusted as
genuine legacy plaintext (the only thing Python's sqlite3 module ever
returns for a value actually written as `str`, i.e. by code older than
this feature) and returned unchanged; a `bytes` value MUST be valid,
authenticated ciphertext of the current format or decryption raises --
there is no partial/best-effort decode path for bytes.
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
MAGIC = b"RNAM"
FORMAT_VERSION = b"\x02"
TEXT_MAGIC = b"RTXT"
TEXT_FORMAT_VERSION = b"\x01"
KEYSTORE_SUFFIX = ".pii_keystore"
RECOVERY_SIDECAR_SUFFIX = ".pii_recovery"
RECOVERY_MAGIC = b"RREC\x01"
CENTRAL_KEK_ENV_VAR = "ROTA_CENTRAL_KEK"

_DPAPI_MARKER = b"\x01"
_CENTRAL_MARKER = b"\x02"


class KeyProtectionUnavailable(ValueError):
    """No runtime key protector could be selected: not Windows (so no
    DPAPI) and ROTA_CENTRAL_KEK is not set. Deliberately never falls back
    to writing a raw, unprotected key file (brief.md E4). Subclasses
    ValueError so api/errors.py's existing generic ValueError->400
    mapping applies without needing to touch that file (out of this
    brief's TASK_SCOPE)."""


class RecoveryFailed(ValueError):
    """A recovery key / central KEK did not unwrap the presented DEK
    material -- wrong secret or corrupted/tampered package. Never
    produces a substitute DEK. Subclasses ValueError for the same reason
    as KeyProtectionUnavailable above."""


class RecoveryKitRequired(ValueError):
    """LOCAL_WINDOWS: raised by rota/application/backup.py when a backup
    is requested before any recovery kit has ever been created for this
    database. Refusing here (R5-02) is deliberate: silently producing a
    backup with no recoverable DEK representation would look identical to
    a real one until the moment the installation is actually lost, which
    is exactly the false sense of security brief.md section 4 forbids."""


# Keyed by the real file path (a stable, safe identity -- unlike id(conn),
# which sqlite3.Connection objects reuse after garbage collection: a first
# version of this cache keyed by id(conn) caused several full-suite tests
# to fail with a wrong-key IntegrityError, because a new connection to a
# DIFFERENT database could reuse the numeric id of an old, already-closed
# connection to a different one). sqlite3.Connection supports neither
# weakref nor arbitrary attributes, so there is no safe way to cache
# anything keyed by connection identity at all -- only by the real path.
_dek_cache_by_path: dict[str, bytes] = {}

# :memory: has no file, so no path to key a persistent cache on. Since a
# :memory: database is never written to disk, "at rest" protection is
# moot for it anyway -- a single random key shared by every :memory:
# connection in this process keeps write-then-read correct within and
# across such connections without needing any per-connection bookkeeping.
_MEMORY_DEK = secrets.token_bytes(KEY_SIZE)


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


def _aes_wrap(payload: bytes, key: bytes) -> bytes:
    nonce = secrets.token_bytes(NONCE_SIZE)
    return nonce + AESGCM(key).encrypt(nonce, payload, None)


def _aes_unwrap(blob: bytes, key: bytes) -> bytes:
    nonce, ciphertext = blob[:NONCE_SIZE], blob[NONCE_SIZE:]
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, None)
    except InvalidTag:
        raise RecoveryFailed("wrong key for this wrapped material") from None


def _central_kek() -> bytes:
    hex_kek = os.environ.get(CENTRAL_KEK_ENV_VAR)
    if not hex_kek:
        raise KeyProtectionUnavailable(f"CENTRAL_SERVICE requires {CENTRAL_KEK_ENV_VAR} to be set")
    try:
        kek = bytes.fromhex(hex_kek)
    except ValueError:
        raise KeyProtectionUnavailable(f"{CENTRAL_KEK_ENV_VAR} is not valid hex") from None
    if len(kek) != KEY_SIZE:
        raise KeyProtectionUnavailable(f"{CENTRAL_KEK_ENV_VAR} must decode to {KEY_SIZE} bytes")
    return kek


def _keystore_path(db_path: Path) -> Path:
    return db_path.with_name(db_path.name + KEYSTORE_SUFFIX)


def recovery_sidecar_path(db_path: str | Path) -> Path:
    """Where create_recovery_kit's persisted (safe, ciphertext) package
    lives, next to db_path -- used by rota/application/backup.py to embed
    it into future backup artifacts."""
    db_path = Path(db_path)
    return db_path.with_name(db_path.name + RECOVERY_SIDECAR_SUFFIX)


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    if not _is_windows():
        os.chmod(tmp, 0o600)
    tmp.replace(path)


def _pack_keystore_payload(dek: bytes, protected_ids: frozenset[str]) -> bytes:
    ids_blob = "\n".join(sorted(protected_ids)).encode("utf-8")
    return dek + len(ids_blob).to_bytes(4, "big") + ids_blob


def _unpack_keystore_payload(payload: bytes) -> tuple[bytes, frozenset[str]]:
    dek = payload[:KEY_SIZE]
    ids_len = int.from_bytes(payload[KEY_SIZE:KEY_SIZE + 4], "big")
    ids_blob = payload[KEY_SIZE + 4:KEY_SIZE + 4 + ids_len]
    ids = frozenset(line for line in ids_blob.decode("utf-8").splitlines() if line)
    return dek, ids


def _load_keystore_raw(ks_path: Path) -> tuple[bytes, bytes]:
    """Returns (marker, unwrapped payload). The payload is DEK +
    protected-ids, packed by _pack_keystore_payload -- see mark_encrypted
    for why these live in the SAME DPAPI/AES-GCM-wrapped blob rather than
    a separate sidecar file (R5-01/R6: a separate file can just be
    deleted to silently reset "nothing is protected"; this cannot, since
    removing or corrupting it destroys the DEK too, which already fails
    closed loudly for every real ciphertext row -- see module docstring)."""
    blob = ks_path.read_bytes()
    marker, rest = blob[:1], blob[1:]
    if marker == _DPAPI_MARKER:
        if not _is_windows():
            raise KeyProtectionUnavailable("existing keystore is DPAPI-protected but this host is not Windows")
        return marker, _dpapi_unprotect(rest)
    if marker == _CENTRAL_MARKER:
        return marker, _aes_unwrap(rest, _central_kek())
    raise ValueError(f"unrecognized keystore protector marker in {ks_path}")


def _save_keystore_raw(ks_path: Path, marker: bytes, payload: bytes) -> None:
    if marker == _DPAPI_MARKER:
        protected = marker + _dpapi_protect(payload)
    elif marker == _CENTRAL_MARKER:
        protected = marker + _aes_wrap(payload, _central_kek())
    else:
        raise ValueError(f"unrecognized protector marker {marker!r}")
    _write_atomic(ks_path, protected)


def protector_kind_for(db_path: str | Path) -> str | None:
    """"DPAPI" | "CENTRAL" for an existing keystore, else None (no DEK
    created yet for this path). Lets backup.py decide which recoverable
    wrapped-DEK representation belongs in a backup artifact."""
    ks_path = _keystore_path(Path(db_path))
    if not ks_path.exists():
        return None
    marker = ks_path.read_bytes()[:1]
    if marker == _DPAPI_MARKER:
        return "DPAPI"
    if marker == _CENTRAL_MARKER:
        return "CENTRAL"
    raise ValueError(f"unrecognized keystore protector marker in {ks_path}")


def _get_or_create_dek_for_path(db_path: Path) -> bytes:
    ks_path = _keystore_path(db_path)
    if ks_path.exists():
        _marker, payload = _load_keystore_raw(ks_path)
        dek, _ids = _unpack_keystore_payload(payload)
        return dek

    dek = secrets.token_bytes(KEY_SIZE)
    if os.environ.get(CENTRAL_KEK_ENV_VAR):
        marker = _CENTRAL_MARKER
    elif _is_windows():
        marker = _DPAPI_MARKER
    else:
        raise KeyProtectionUnavailable(
            f"no runtime key protector available: set {CENTRAL_KEK_ENV_VAR} for CENTRAL_SERVICE "
            "or run on Windows for LOCAL_WINDOWS (DPAPI) -- no automatic raw-key-file fallback"
        )
    _save_keystore_raw(ks_path, marker, _pack_keystore_payload(dek, frozenset()))
    return dek


def _main_db_file(conn: sqlite3.Connection) -> str:
    """Empty string for :memory: / a temporary on-disk database, per
    PRAGMA database_list's own documented convention."""
    for _seq, name, file in conn.execute("PRAGMA database_list").fetchall():
        if name == "main":
            return file
    return ""


def mark_encrypted(conn: sqlite3.Connection, employee_id: str) -> None:
    """R5-01/R6: a genuine legacy row (written before this feature
    existed) is the ONLY thing decrypt_name should ever trust as plain
    `str` -- but SQLite's storage class alone cannot prove that on its
    own: a single UPDATE can put an ordinary Python `str` into a column
    that used to hold ciphertext, and nothing about that byte sequence
    records it was ever anything else. This registry is the record: once
    an employee_id has ever been written through encrypt_name,
    employee_repository._row_to_employee refuses to accept a `str` for
    that id ever again, no matter what the column's storage class says
    later. It lives INSIDE the same DPAPI/AES-GCM-wrapped keystore blob
    as the DEK (see _load_keystore_raw), not a separate sidecar file --
    a first version used a plain, unauthenticated `.pii_protected_ids`
    sidecar, which Codex's R6 audit broke by simply deleting that one
    file while leaving the keystore (and the DEK it protects) untouched,
    silently resetting the registry to "nothing is protected" without
    disturbing anything else. Folding it into the keystore's own
    authenticated payload means the only way to erase this record is to
    also destroy/corrupt the DEK, which already fails closed loudly (a
    real ciphertext row raises an integrity error) rather than silently
    -- the exact fail-closed behavior brief.md E9/section 3 requires.
    :memory: has no file and no persisted downgrade threat model, so
    this is a no-op there. If somehow called before any keystore exists
    (resolve_key always creates one first in every real write path),
    there is no DEK yet to bind this registry to, so there is nothing to
    mark -- also a no-op."""
    path = _main_db_file(conn)
    if not path:
        return
    ks_path = _keystore_path(Path(path))
    if not ks_path.exists():
        return
    marker, payload = _load_keystore_raw(ks_path)
    dek, ids = _unpack_keystore_payload(payload)
    if employee_id in ids:
        return
    _save_keystore_raw(ks_path, marker, _pack_keystore_payload(dek, ids | {employee_id}))


def load_protected_ids(conn: sqlite3.Connection) -> frozenset[str]:
    """Callers resolve this ONCE per repository-level call, same
    N+1-safety rule as resolve_key -- it is a file read, not a SQL
    statement, but there is no reason to repeat it per row either."""
    path = _main_db_file(conn)
    if not path:
        return frozenset()
    ks_path = _keystore_path(Path(path))
    if not ks_path.exists():
        return frozenset()
    _marker, payload = _load_keystore_raw(ks_path)
    _dek, ids = _unpack_keystore_payload(payload)
    return ids


def resolve_key(conn: sqlite3.Connection) -> bytes:
    """Callers resolve this ONCE per repository-level call (get_employee,
    list_employees, ...) and pass the result down to encrypt_name/
    decrypt_name for every row -- never once per row. PRAGMA database_list
    is a real executed SQL statement; calling it per row breaks the exact
    query-count guarantee tests/test_t019.py::test_23_n_plus_1_oracle
    enforces."""
    path = _main_db_file(conn)
    if not path:
        return _MEMORY_DEK
    if path not in _dek_cache_by_path:
        _dek_cache_by_path[path] = _get_or_create_dek_for_path(Path(path))
    return _dek_cache_by_path[path]


def encrypt_name(key: bytes, plaintext: str) -> bytes:
    aad = MAGIC + FORMAT_VERSION
    nonce = secrets.token_bytes(NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), aad)
    return aad + nonce + ciphertext


def decrypt_name(key: bytes, stored: bytes | str) -> str:
    """A `str` value is genuine legacy plaintext -- the only thing
    Python's sqlite3 module returns for a value actually written as
    `str` by code older than this feature -- and is returned unchanged.
    A `bytes` value must be a complete, authenticated, current-version
    ciphertext or this raises; there is no best-effort/replace decode for
    bytes, so a corrupted or deliberately downgraded header cannot be
    silently read as if it were plaintext (brief.md E9)."""
    if isinstance(stored, str):
        return stored
    header_len = len(MAGIC) + len(FORMAT_VERSION)
    if len(stored) < header_len + NONCE_SIZE:
        raise ValueError("employee display_name is too short to be a valid encrypted value")
    aad = stored[:header_len]
    if not aad.startswith(MAGIC):
        raise ValueError("employee display_name has an unrecognized header -- not a legacy string and not valid ciphertext")
    version = aad[len(MAGIC):]
    if version != FORMAT_VERSION:
        raise ValueError(f"employee display_name has unsupported ciphertext format version {version!r}")
    rest = stored[header_len:]
    nonce, ciphertext = rest[:NONCE_SIZE], rest[NONCE_SIZE:]
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, aad).decode("utf-8")
    except InvalidTag:
        raise ValueError("employee display_name failed integrity check -- possibly corrupted or tampered") from None


def create_recovery_kit(dek: bytes) -> tuple[bytes, bytes]:
    """LOCAL_WINDOWS only. Returns (recovery_package, recovery_key).
    recovery_package (the DEK wrapped by recovery_key) is safe to store
    with a backup -- it is ciphertext. recovery_key is the actual secret
    that unwraps it and MUST be handed to the installation owner for
    separate safekeeping; this module never persists it anywhere."""
    recovery_key = secrets.token_bytes(KEY_SIZE)
    package = RECOVERY_MAGIC + _aes_wrap(dek, recovery_key)
    return package, recovery_key


def recover_dek_from_kit(recovery_package: bytes, recovery_key: bytes) -> bytes:
    if not recovery_package.startswith(RECOVERY_MAGIC):
        raise RecoveryFailed("not a recognized recovery package")
    return _aes_unwrap(recovery_package[len(RECOVERY_MAGIC):], recovery_key)


def wrap_dek_for_central_backup(dek: bytes) -> bytes:
    """CENTRAL_SERVICE only: wraps the DEK with the SAME externally-supplied
    KEK already protecting it at runtime, so recovery re-supplies that
    same deployment secret independently of this machine/process -- the
    deployment's own management of ROTA_CENTRAL_KEK IS the recovery
    capability here, not a second mechanism this module invents."""
    return _CENTRAL_MARKER + _aes_wrap(dek, _central_kek())


def unwrap_dek_from_central_backup(wrapped: bytes) -> bytes:
    marker, rest = wrapped[:1], wrapped[1:]
    if marker != _CENTRAL_MARKER:
        raise RecoveryFailed("not a recognized central-service wrapped DEK")
    return _aes_unwrap(rest, _central_kek())


# ---------------------------------------------------------------------------
# ROTA-RODO-DISPLAY-NAME-LEAKS-OUTSIDE-EMPLOYEES-TABLE (brief.md exact SHA
# 5683bac, section 2): a general, versioned, record-bound AEAD envelope for
# arbitrary text/JSON -- reused by plan_preview_repository.py's
# warnings_json and site_memory.py's decision_required_snapshots.payload_json
# instead of copying encrypt_name/decrypt_name's algorithm into each
# repository. Same DEK/runtime-protector contract as Employee.display_name
# (resolve_key); no second key or key-management model.
#
# Record-bound AAD (section 2.1): the caller supplies `aad`, built via
# bind_aad() from canonical values already on hand at the call site (e.g.
# site_id + month for a preview, decision_required_id for a snapshot). This
# is NOT stored in the ciphertext blob -- the caller reconstructs the exact
# same bytes from the row's own already-known columns at read time. Binding
# it into the AEAD tag means copying one whole, validly-decryptable
# ciphertext blob from one record into a different record of the same class
# fails the same authenticated way real corruption would (brief.md L4a/L4b):
# the tag was computed over THIS record's AAD, not the one it got pasted
# into.
# ---------------------------------------------------------------------------


def bind_aad(class_label: str, *parts: str) -> bytes:
    """Deterministic AAD from canonical values already known to the caller.
    NUL-separated so e.g. ("AB", "C") and ("A", "BC") never collide."""
    return b"\x00".join(part.encode("utf-8") for part in (class_label, *parts))


def encrypt_text(key: bytes, plaintext: str, aad: bytes) -> bytes:
    header = TEXT_MAGIC + TEXT_FORMAT_VERSION
    full_aad = header + aad
    nonce = secrets.token_bytes(NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), full_aad)
    return header + nonce + ciphertext


def decrypt_text(key: bytes, stored: bytes | str, aad: bytes) -> str:
    """Same str/bytes trust split as decrypt_name: a genuine `str` (legacy,
    written before this feature existed) is returned unchanged; a `bytes`
    value must be complete, current-version ciphertext authenticated under
    THIS EXACT aad, or this raises -- including when it is otherwise
    perfectly valid ciphertext for a DIFFERENT record of the same class
    (wrong aad = wrong tag = InvalidTag, per bind_aad's docstring above)."""
    if isinstance(stored, str):
        return stored
    header_len = len(TEXT_MAGIC) + len(TEXT_FORMAT_VERSION)
    if len(stored) < header_len + NONCE_SIZE:
        raise ValueError("encrypted value is too short to be valid")
    header = stored[:header_len]
    if not header.startswith(TEXT_MAGIC):
        raise ValueError("encrypted value has an unrecognized header -- not a legacy string and not valid ciphertext")
    version = header[len(TEXT_MAGIC):]
    if version != TEXT_FORMAT_VERSION:
        raise ValueError(f"encrypted value has unsupported ciphertext format version {version!r}")
    rest = stored[header_len:]
    nonce, ciphertext = rest[:NONCE_SIZE], rest[NONCE_SIZE:]
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, header + aad).decode("utf-8")
    except InvalidTag:
        raise ValueError("encrypted value failed integrity check -- possibly corrupted, tampered, or copied from a different record") from None
