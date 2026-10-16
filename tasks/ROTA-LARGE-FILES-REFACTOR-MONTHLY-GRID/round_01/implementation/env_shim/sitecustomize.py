# ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID evidence environment ONLY (never
# production, never committed outside round_01/): the Linux cloud container
# has no Windows DPAPI, so LOCAL_WINDOWS pii_crypto cannot create its
# keystore and every employee write fails (KeyProtectionUnavailable). This
# makes the DPAPI protector a pass-through so the e2e backend can run on
# Linux. It changes nothing in the grid/UI path under test.
import rota.persistence.pii_crypto as _pc

_pc._is_windows = lambda: True
_pc._dpapi_protect = lambda data: bytes(data)
_pc._dpapi_unprotect = lambda data: bytes(data)
