"""ROTA-T021 Wydruk Grafiku: vertical API test for the new thin marshalling
router (api/routers/export.py) plus the one new small application wrapper
it required (durable_inputs.save_print_settings -- a spec-flagged gap,
save side only, no new validation of its own). generate_schedule_pdf
itself (T020) is unchanged and already has its own dedicated, extensive
test matrix in tests/test_t020.py -- not copied here. This file proves
the router's marshalling: print-settings GET/PUT roundtrip, a validation
failure mapping to 422, and the two problem codes reachable from a bare
site (no print settings, no current schedule) getting their real Polish
messages, never a raw code."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from api.routers.export import PROBLEM_MESSAGE_PL
from rota.domain import CoordinatorSiteAssociation
from rota.persistence.coordinator_repository import save_coordinator_site_association
from rota.persistence.db import connect
from tests.support.t008_fixtures import seed_base_entities

SITE = "SITE-1"
COORD = DEV_COORDINATOR_ID

VALID_SETTINGS_PAYLOAD = {
    "company_print_name": "ELNATH DEMO",
    "site_print_name": "SITE-DEMO",
    "base_regime": "12h",
    "work_code_intervals": {
        "D1": {"start_time": "06:00", "end_time": "18:00", "end_next_day": False}, "D2": None, "D3": None, "D4": None, "D5": None,
        "N1": {"start_time": "18:00", "end_time": "06:00", "end_next_day": True},
        "N2": {"start_time": "00:00", "end_time": "16:00", "end_next_day": False}, "N3": None, "N4": None, "N5": None,
    },
    "reserve_hours": {k: None for k in ("U3", "U4", "U5", "C3", "C4", "C5")},
}


@pytest.fixture
def conn():
    connection = connect(":memory:")
    seed_base_entities(connection, site_id=SITE, coordinator_id=COORD)
    save_coordinator_site_association(connection, CoordinatorSiteAssociation(COORD, SITE, True))
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def client(conn):
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_conn, None)


def test_no_print_settings_returns_null(client):
    resp = client.get(f"/api/workspace/sites/{SITE}/print-settings")
    assert resp.status_code == 200
    assert resp.json() is None


def test_save_and_read_back_print_settings(client):
    put_resp = client.put(f"/api/workspace/sites/{SITE}/print-settings", json=VALID_SETTINGS_PAYLOAD)
    assert put_resp.status_code == 204

    get_resp = client.get(f"/api/workspace/sites/{SITE}/print-settings")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["site_id"] == SITE
    assert body["work_code_intervals"]["D1"] == {"start_time": "06:00", "end_time": "18:00", "end_next_day": False}
    assert body["work_code_intervals"]["D2"] is None


def test_invalid_base_regime_is_rejected_with_422(client):
    bad = dict(VALID_SETTINGS_PAYLOAD, base_regime="8h")
    resp = client.put(f"/api/workspace/sites/{SITE}/print-settings", json=bad)
    assert resp.status_code == 422


def test_export_without_print_settings_is_polish_and_specific(client):
    resp = client.post(f"/api/workspace/sites/{SITE}/schedule/{date(2026, 8, 1).isoformat()}/export", json={"period_label": "sierpień 2026"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["problem_code"] == "PRINT_SETTINGS_MISSING"
    assert body["message"] == PROBLEM_MESSAGE_PL["PRINT_SETTINGS_MISSING"]


def test_export_with_settings_but_no_schedule_is_polish_and_specific(client):
    client.put(f"/api/workspace/sites/{SITE}/print-settings", json=VALID_SETTINGS_PAYLOAD)
    resp = client.post(f"/api/workspace/sites/{SITE}/schedule/{date(2026, 8, 1).isoformat()}/export", json={"period_label": "sierpień 2026"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["problem_code"] == "NO_CURRENT_SCHEDULE"
    assert body["message"] == PROBLEM_MESSAGE_PL["NO_CURRENT_SCHEDULE"]


if __name__ == "__main__":
    print("test_t021_export_api module OK")
