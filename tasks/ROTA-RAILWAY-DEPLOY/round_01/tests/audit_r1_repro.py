from __future__ import annotations

import secrets

from rota.persistence import pii_crypto


def test_documented_central_kek_generation_produces_a_valid_runtime_kek(monkeypatch):
    """deploy/RAILWAY.md says to use this command for each deployment secret."""
    documented_value = secrets.token_urlsafe(32)
    monkeypatch.setenv(pii_crypto.CENTRAL_KEK_ENV_VAR, documented_value)

    parsed = pii_crypto._central_kek()

    assert len(parsed) == pii_crypto.KEY_SIZE
