from __future__ import annotations

import secrets

from rota.persistence import pii_crypto


def test_currently_documented_central_kek_generation_is_accepted(monkeypatch):
    documented_value = secrets.token_hex(32)
    monkeypatch.setenv(pii_crypto.CENTRAL_KEK_ENV_VAR, documented_value)

    parsed = pii_crypto._central_kek()

    assert len(documented_value) == 64
    assert parsed == bytes.fromhex(documented_value)
    assert len(parsed) == pii_crypto.KEY_SIZE
