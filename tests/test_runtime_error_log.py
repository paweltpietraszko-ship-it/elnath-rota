"""ROTA-TECHNICAL-ERROR-RECOVERY-UX (brief.md exact SHA fe689a1): narrow
test matrix for the one sanitized runtime error log -- module-level
behavior (rotation, incident_id, deployment-model directory resolution),
the api/errors.py unhandled-exception boundary (A1), the shared PLAN/
REPLAN/wider-search/retry boundary (A2/A6/A15), and the diagnostic ZIP
embedding (A8). One vertical integration pion (brief.md section 10):
a real unclassified exception -> HTTP response -> runtime log -> ZIP.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from api import runtime_log
from api.deps import get_conn
from api.errors import to_http_exception
from api.main import app
from api.routers.schedule import _planning_result_out
from api.runtime_log import RuntimeLogConfigurationError, log_runtime_error, resolve_log_dir
from rota.application.backup import build_diagnostic_zip
from rota.persistence.coordinator_repository import save_coordinator_site_association
from rota.persistence.db import connect
from rota.domain import CoordinatorSiteAssociation
from rota.planning.engine_types import PlanningResult
from tests.support.t008_fixtures import seed_base_entities

SITE = "SITE-1"
COORD = "COORD-1"


@pytest.fixture(autouse=True)
def _reset_runtime_log(tmp_path, monkeypatch):
    monkeypatch.delenv("ROTA_CENTRAL_KEK", raising=False)
    monkeypatch.delenv("ROTA_LOG_DIR", raising=False)
    monkeypatch.setenv("ROTA_LOG_DIR", str(tmp_path / "logs"))
    runtime_log.reset_for_tests()
    yield
    runtime_log.reset_for_tests()


def _log_path(tmp_path) -> "os.PathLike":
    return tmp_path / "logs" / runtime_log.LOG_FILENAME


def test_incident_id_unique_per_call(tmp_path):
    id1 = log_runtime_error(component="API", safe_message="x", exception_type="TEST")
    id2 = log_runtime_error(component="API", safe_message="x", exception_type="TEST")
    assert id1 != id2


def test_entry_contains_required_fields_no_raw_exception_message(tmp_path):
    # Codex R3-01 (exact 05f2e2a): neither the exception's own str() nor a
    # raise statement's literal source-line text may reach the log -- only
    # a bare file/line/function frame trail plus the caller's own fixed
    # safe_message.
    def _raise_with_domain_value():
        raise ValueError("Jan Kowalski token=OWNER-SECRET-7391")

    try:
        _raise_with_domain_value()
    except ValueError as exc:
        incident_id = log_runtime_error(component="API", safe_message="Nieobsłużony wyjątek backendu.", exc=exc)
    content = _log_path(tmp_path).read_text(encoding="utf-8")
    assert incident_id in content
    assert "ERROR [API]" in content
    assert "type=ValueError" in content
    assert "Nieobsłużony wyjątek backendu." in content
    assert "_raise_with_domain_value" in content  # a real frame is still present
    assert "Jan Kowalski token=OWNER-SECRET-7391" not in content


def test_structured_planning_failure_never_copies_raw_error_message(tmp_path):
    result = PlanningResult(
        status="TECHNICAL_ERROR", candidates=[], decision_payload=None,
        error_message="zawiera Jan Kowalski i inne dane wrażliwe", warnings=[], optimization_complete=True,
    )
    conn = connect(":memory:")
    seed_base_entities(conn, site_id=SITE, coordinator_id=COORD)
    _planning_result_out(conn, result, operation="PLAN")
    conn.close()
    content = _log_path(tmp_path).read_text(encoding="utf-8")
    assert "STRUCTURED_PLANNING_FAILURE" in content
    assert "[PLAN]" in content
    assert "Jan Kowalski" not in content


def test_structured_planning_failure_has_no_stack_trace(tmp_path):
    result = PlanningResult(
        status="TECHNICAL_ERROR", candidates=[], decision_payload=None,
        error_message=None, warnings=[], optimization_complete=True,
    )
    conn = connect(":memory:")
    seed_base_entities(conn, site_id=SITE, coordinator_id=COORD)
    _planning_result_out(conn, result, operation="REPLAN")
    conn.close()
    content = _log_path(tmp_path).read_text(encoding="utf-8")
    lines = [line for line in content.splitlines() if line.strip()]
    assert len(lines) == 1  # exactly one entry, single line -- no stack trace appended
    assert "[REPLAN]" in lines[0]


def test_feasible_result_does_not_log(tmp_path):
    result = PlanningResult(
        status="FEASIBLE", candidates=[], decision_payload=None,
        error_message=None, warnings=[], optimization_complete=True,
    )
    conn = connect(":memory:")
    seed_base_entities(conn, site_id=SITE, coordinator_id=COORD)
    _planning_result_out(conn, result, operation="PLAN")
    conn.close()
    assert not _log_path(tmp_path).exists()


def test_central_service_requires_log_dir(monkeypatch):
    monkeypatch.setenv("ROTA_CENTRAL_KEK", "aa" * 32)
    monkeypatch.delenv("ROTA_LOG_DIR", raising=False)
    with pytest.raises(RuntimeLogConfigurationError):
        resolve_log_dir()


def test_central_service_uses_configured_log_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("ROTA_CENTRAL_KEK", "aa" * 32)
    monkeypatch.setenv("ROTA_LOG_DIR", str(tmp_path / "central-logs"))
    assert resolve_log_dir() == tmp_path / "central-logs"


def test_local_windows_defaults_next_to_db_path(monkeypatch, tmp_path):
    monkeypatch.delenv("ROTA_CENTRAL_KEK", raising=False)
    monkeypatch.delenv("ROTA_LOG_DIR", raising=False)
    monkeypatch.setattr("api.runtime_log.DB_PATH", str(tmp_path / "rota_dev.db"))
    assert resolve_log_dir() == (tmp_path / "logs").resolve()


def test_rotation_keeps_current_plus_four_copies(tmp_path):
    # brief.md A7: max current file + 4 rotated copies, older ones deleted.
    # 3000 entries * ~5KB >> 5 MiB (the 1 MiB cap * 4 backups), comfortably
    # forcing wraparound past backupCount so the oldest are actually
    # dropped, not just "rotated at least once".
    big_message = "x" * 5000
    for _ in range(3000):
        log_runtime_error(component="API", safe_message=big_message, exception_type="TEST")
    log_dir = tmp_path / "logs"
    rotated = sorted(p.name for p in log_dir.glob(f"{runtime_log.LOG_FILENAME}*"))
    assert runtime_log.LOG_FILENAME in rotated
    backups = [n for n in rotated if n != runtime_log.LOG_FILENAME]
    assert len(backups) == 4
    for name in backups:
        assert name.startswith(f"{runtime_log.LOG_FILENAME}.")


def test_diagnostic_zip_embeds_runtime_logs_when_present(tmp_path):
    import zipfile

    log_runtime_error(component="API", safe_message="x", exception_type="TEST")
    conn = connect(":memory:")
    seed_base_entities(conn, site_id=SITE, coordinator_id=COORD)
    dest = tmp_path / "diag.zip"
    build_diagnostic_zip(conn, str(dest), runtime_log_dir=tmp_path / "logs")
    conn.close()
    with zipfile.ZipFile(dest) as archive:
        names = archive.namelist()
    assert f"logs/{runtime_log.LOG_FILENAME}" in names


def test_diagnostic_zip_works_without_runtime_log(tmp_path):
    import zipfile

    conn = connect(":memory:")
    seed_base_entities(conn, site_id=SITE, coordinator_id=COORD)
    dest = tmp_path / "diag.zip"
    build_diagnostic_zip(conn, str(dest), runtime_log_dir=tmp_path / "logs-does-not-exist")
    conn.close()
    with zipfile.ZipFile(dest) as archive:
        names = archive.namelist()
    assert "diagnostics.json" in names
    assert not any(n.startswith("logs/") for n in names)


# --- Vertical integration pion (brief.md section 10): real unhandled
# exception -> HTTP -> runtime log -> diagnostic ZIP. -------------------


def test_unhandled_exception_end_to_end_reaches_log_and_diagnostic_zip(tmp_path, monkeypatch):
    connection = connect(":memory:")
    seed_base_entities(connection, site_id=SITE, coordinator_id=COORD)
    save_coordinator_site_association(connection, CoordinatorSiteAssociation(COORD, SITE, True))
    app.dependency_overrides[get_conn] = lambda: (yield connection)

    def _boom(*args, **kwargs):
        raise RuntimeError("a genuinely unclassified internal bug, never a domain exception")

    import api.routers.schedule as schedule_router
    monkeypatch.setattr(schedule_router, "plan_month", _boom)
    try:
        client = TestClient(app)
        resp = client.post(
            f"/api/workspace/sites/{SITE}/schedule/2026-08-01/plan",
            json={"effective_from": "2026-08-01"},
        )
        assert resp.status_code == 500
        assert resp.headers.get("X-Elnath-Public-Error") == "1"
        assert resp.json()["detail"] == "Wystąpiła awaria techniczna. Wyłącz aplikację i uruchom ją ponownie."
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()

    log_content = _log_path(tmp_path).read_text(encoding="utf-8")
    assert "[API]" in log_content
    assert "type=RuntimeError" in log_content
    assert "_boom" in log_content  # a real frame from the actual stack trace
    assert "a genuinely unclassified internal bug" not in log_content  # never the exception's own str()

    dest = tmp_path / "diag.zip"
    conn2 = connect(":memory:")
    seed_base_entities(conn2, site_id=SITE, coordinator_id=COORD)
    build_diagnostic_zip(conn2, str(dest), runtime_log_dir=tmp_path / "logs")
    conn2.close()
    import zipfile

    with zipfile.ZipFile(dest) as archive:
        assert f"logs/{runtime_log.LOG_FILENAME}" in archive.namelist()


def test_to_http_exception_directly_logs_unclassified_exception(tmp_path):
    exc = RuntimeError("a genuinely unclassified internal error")
    http_exc = to_http_exception(exc)
    assert http_exc.status_code == 500
    assert http_exc.detail == "Wystąpiła awaria techniczna. Wyłącz aplikację i uruchom ją ponownie."
    content = _log_path(tmp_path).read_text(encoding="utf-8")
    assert "type=RuntimeError" in content


def test_classified_domain_exception_does_not_log(tmp_path):
    from rota.persistence.employee_repository import EmployeeNotFound

    exc = EmployeeNotFound("EMP-999")
    to_http_exception(exc)
    assert not _log_path(tmp_path).exists()


def test_dependency_exception_reaches_global_handler_logged_and_public(tmp_path):
    # Codex R3-02 (exact 05f2e2a): a router's own try/except only ever
    # covers its own body -- a FastAPI dependency failure (get_conn here)
    # never reaches it. api/main.py's global Exception handler is the only
    # other boundary, and must log exactly once and return the same
    # frozen public message T060 already promises everywhere else.
    def _broken_dependency():
        raise RuntimeError("dependency failed with token=SECRET-DEPENDENCY")

    app.dependency_overrides[get_conn] = _broken_dependency
    try:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/workspace/sites")
        assert resp.status_code == 500
        assert resp.headers.get("X-Elnath-Public-Error") == "1"
        assert resp.json()["detail"] == "Wystąpiła awaria techniczna. Wyłącz aplikację i uruchom ją ponownie."
    finally:
        app.dependency_overrides.pop(get_conn, None)
    content = _log_path(tmp_path).read_text(encoding="utf-8")
    assert content.count("type=RuntimeError") == 1  # exactly one entry, never double-logged
    assert "SECRET-DEPENDENCY" not in content


if __name__ == "__main__":
    print("test_runtime_error_log module OK")
