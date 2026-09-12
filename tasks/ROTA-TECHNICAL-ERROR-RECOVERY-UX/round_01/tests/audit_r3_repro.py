"""Independent reproducers for implementation audit on 05f2e2a."""
from __future__ import annotations

import zipfile

import pytest
from fastapi.testclient import TestClient

from api import runtime_log
from api.deps import get_conn
from api.errors import to_http_exception
from api.main import app
from rota.application.backup import build_diagnostic_zip
from rota.persistence.coordinator_repository import save_coordinator_site_association
from rota.persistence.db import connect
from rota.domain import CoordinatorSiteAssociation
from rota.planning.engine_types import PlanningResult
from tests.support.t008_fixtures import seed_base_entities


SITE = "SITE-R3"
COORDINATOR = "DEV-COORD-1"


@pytest.fixture(autouse=True)
def _isolated_runtime_log(tmp_path, monkeypatch):
    monkeypatch.delenv("ROTA_CENTRAL_KEK", raising=False)
    monkeypatch.setenv("ROTA_LOG_DIR", str(tmp_path / "logs"))
    runtime_log.reset_for_tests()
    yield
    app.dependency_overrides.pop(get_conn, None)
    runtime_log.reset_for_tests()


def test_r3_private_exception_text_is_absent_from_runtime_log_and_zip(tmp_path):
    """Brief A5 and section 3 prohibit names, tokens and raw domain content."""
    private_text = "Jan Kowalski token=OWNER-SECRET-7391"
    try:
        raise RuntimeError(private_text)
    except RuntimeError as exc:
        response = to_http_exception(exc)

    assert response.status_code == 500
    log_path = tmp_path / "logs" / runtime_log.LOG_FILENAME
    log_content = log_path.read_text(encoding="utf-8")

    conn = connect(":memory:")
    destination = tmp_path / "diagnostics.zip"
    try:
        build_diagnostic_zip(conn, str(destination), runtime_log_dir=tmp_path / "logs")
    finally:
        conn.close()
    with zipfile.ZipFile(destination) as archive:
        bundled = archive.read(f"logs/{runtime_log.LOG_FILENAME}").decode("utf-8")
    assert private_text not in log_content
    assert private_text not in bundled


def test_r3_dependency_exception_is_logged_and_returns_public_recovery_message(tmp_path):
    """A1 covers an unhandled backend exception, including before router code."""

    def broken_connection_dependency():
        raise RuntimeError("dependency failed with token=SECRET-DEPENDENCY")

    app.dependency_overrides[get_conn] = broken_connection_dependency
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/workspace/sites")

    assert response.status_code == 500
    assert response.headers.get("X-Elnath-Public-Error") == "1"
    assert response.json()["detail"] == (
        "Wystąpiła awaria techniczna. Wyłącz aplikację i uruchom ją ponownie."
    )
    log_path = tmp_path / "logs" / runtime_log.LOG_FILENAME
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "type=RuntimeError" in content
    assert "SECRET-DEPENDENCY" not in content


@pytest.mark.parametrize(
    ("path_suffix", "function_name", "payload"),
    [
        ("plan", "plan_month", {"effective_from": "2026-08-01"}),
        ("replan", "replan", {"effective_from": "2026-08-01"}),
        ("replan/wider-search", "replan_wider_search", {}),
        ("replan/retry", "replan_retry_narrow", {}),
    ],
)
def test_r3_each_planning_endpoint_logs_one_structured_failure(
    tmp_path, monkeypatch, path_suffix, function_name, payload,
):
    """A2/A15 matrix: all four real endpoints cross the single boundary once."""
    connection = connect(":memory:")
    seed_base_entities(connection, site_id=SITE, coordinator_id=COORDINATOR)
    save_coordinator_site_association(
        connection, CoordinatorSiteAssociation(COORDINATOR, SITE, True),
    )
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    result = PlanningResult(
        status="TECHNICAL_ERROR", candidates=[], decision_payload=None,
        error_message="RAW EMPLOYEE NAME", warnings=[],
    )
    import api.routers.schedule as schedule_router

    monkeypatch.setattr(schedule_router, function_name, lambda *args, **kwargs: result)
    try:
        response = TestClient(app).post(
            f"/api/workspace/sites/{SITE}/schedule/2026-08-01/{path_suffix}",
            json=payload,
        )
    finally:
        connection.close()

    assert response.status_code == 200
    content = (tmp_path / "logs" / runtime_log.LOG_FILENAME).read_text(encoding="utf-8")
    assert content.count("STRUCTURED_PLANNING_FAILURE") == 1
    assert "RAW EMPLOYEE NAME" not in content
