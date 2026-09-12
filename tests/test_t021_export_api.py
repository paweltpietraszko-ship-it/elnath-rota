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
from api.routers.export import PROBLEM_MESSAGE_PL, UNACKNOWLEDGED_LAW_PROBLEM_CODE
from rota.domain import CoordinatorSiteAssociation, ShiftKind
from rota.persistence.coordinator_repository import save_coordinator_site_association
from rota.persistence.db import connect
from rota.persistence.site_repository import save_site_print_settings as _save_print_settings
from tests.support.t008_fixtures import seed_base_entities
from tests.test_t020 import MONTH as T020_MONTH
from tests.test_t020 import _create_version, _seed, _settings, _work_item

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


# --- ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS: router-level P1-P11 round trip.
# Reuses test_t020's fuller fixture (real SiteMembership etc.), not this
# file's own minimal one, since REST-01 needs a real work-period pair.


@pytest.fixture
def rest01_conn():
    connection = connect(":memory:")
    _seed(connection)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def rest01_client(rest01_conn):
    app.dependency_overrides[get_conn] = lambda: (yield rest01_conn)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_conn, None)


def _seed_rest01_schedule(conn) -> None:
    # Same REST-01 shape as tests/test_export_unacknowledged_law.py: D 06-18
    # day1, N 00-16 day2 -- 6h gap, below the 11h REST_MIN_HOURS fallback.
    save_coordinator_site_association(conn, CoordinatorSiteAssociation("COORD-1", "SITE-1", True))
    demand1, a1 = _work_item(1, 6, 18, kind=ShiftKind.D)
    demand2, a2 = _work_item(2, 0, 16, kind=ShiftKind.N)
    _create_version(conn, [demand1, demand2], [a1, a2])


def _export_via_http(client, acknowledged=None):
    payload = {"period_label": "sierpień 2026"}
    if acknowledged is not None:
        payload["acknowledged_law_fingerprints"] = acknowledged
    return client.post(f"/api/workspace/sites/SITE-1/schedule/{T020_MONTH.isoformat()}/export", json=payload)


def test_p1_working_without_law_still_prints_via_http(rest01_client, rest01_conn):
    _save_print_settings(rest01_conn, _settings())
    save_coordinator_site_association(rest01_conn, CoordinatorSiteAssociation("COORD-1", "SITE-1", True))
    demand, a = _work_item(1, 6, 18, kind=ShiftKind.D)
    _create_version(rest01_conn, [demand], [a])
    resp = _export_via_http(rest01_client)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_p3_fresh_law_blocks_and_lists_fingerprint_via_http(rest01_client, rest01_conn):
    _save_print_settings(rest01_conn, _settings())
    _seed_rest01_schedule(rest01_conn)
    resp = _export_via_http(rest01_client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["problem_code"] == UNACKNOWLEDGED_LAW_PROBLEM_CODE
    assert body["fresh_law"] is not None
    assert len(body["fresh_law"]) == 1
    item = body["fresh_law"][0]
    assert item["category"] == "LAW"
    assert item["label"] == "odpoczynek dobowy"
    assert item["affected_assignment_or_employee"] == "EMP-1"
    assert item["fingerprint"]


def test_p4_direct_post_without_fingerprints_is_blocked_via_http(rest01_client, rest01_conn):
    _save_print_settings(rest01_conn, _settings())
    _seed_rest01_schedule(rest01_conn)
    # A direct POST with no acknowledged_law_fingerprints field at all --
    # ExportRequest's default (empty list) must still block.
    resp = rest01_client.post(
        f"/api/workspace/sites/SITE-1/schedule/{T020_MONTH.isoformat()}/export",
        json={"period_label": "sierpień 2026"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert resp.json()["problem_code"] == UNACKNOWLEDGED_LAW_PROBLEM_CODE


def test_p5_p7_acknowledging_returned_fingerprint_unblocks_once_via_http(rest01_client, rest01_conn):
    _save_print_settings(rest01_conn, _settings())
    _seed_rest01_schedule(rest01_conn)
    blocked = _export_via_http(rest01_client).json()
    fingerprint = blocked["fresh_law"][0]["fingerprint"]

    ready = _export_via_http(rest01_client, acknowledged=[fingerprint])
    assert ready.json()["ok"] is True

    # P7: the next attempt with no fingerprints is blocked again -- the ack
    # is never persisted.
    again = _export_via_http(rest01_client)
    assert again.json()["ok"] is False
    assert again.json()["problem_code"] == UNACKNOWLEDGED_LAW_PROBLEM_CODE


if __name__ == "__main__":
    print("test_t021_export_api module OK")
