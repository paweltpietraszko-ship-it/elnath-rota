from __future__ import annotations

import inspect
import json
import os
import re
import subprocess
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn as api_get_conn
from api.main import app
from api.routers import bootstrap as bootstrap_router
from api.routers import durable_inputs as durable_inputs_router
from api.routers.bootstrap import CreateSiteRequest, create_site, list_sites
from api.routers.calendar import get_range
from api.routers.durable_inputs import (
    BulkGenerateRequest,
    SetDayRequest,
    bulk_generate,
    set_day,
)
from rota.domain import Coordinator, SitePlanningRegime
from rota.persistence.coordinator_repository import (
    list_associations_for_coordinator,
    save_coordinator,
)
from rota.persistence.db import connect
from rota.persistence.site_profile_repository import get_site_profile
from rota.persistence.site_repository import InvalidSitePrintSettings, get_site


REPO_ROOT = Path(__file__).resolve().parents[4]
ACCEPTED_CONTRACT_SHA = "680a34258f956df26ac6fd9b3190ad4e70c312b0"


@pytest.fixture
def conn(tmp_path):
    connection = connect(str(tmp_path / "t021-r5.db"))
    save_coordinator(connection, Coordinator(DEV_COORDINATOR_ID, "Audytor", True))
    try:
        yield connection
    finally:
        connection.close()


def _create(conn, regime: str = "OCHRONA"):
    return create_site(
        CreateSiteRequest(
            display_name=f"Obiekt {regime}",
            profile_display_name=f"Profil {regime}",
            rolling_7d_decision_threshold_hours=40,
            planning_regime=regime,
        ),
        conn,
    )


@pytest.mark.parametrize("regime", ["OCHRONA", "ORDINARY"])
def test_vertical_create_and_list_preserves_every_contract_field(conn, regime):
    created = _create(conn, regime)

    site = get_site(conn, created.site_id)
    profile = get_site_profile(conn, created.profile_id)
    associations = list_associations_for_coordinator(conn, DEV_COORDINATOR_ID)
    summaries = list_sites(conn)

    assert created.site_id.startswith("SITE-")
    assert created.profile_id.startswith("PROF-")
    assert site.profile_id == created.profile_id
    assert site.display_name == f"Obiekt {regime}"
    assert site.active is True
    assert site.planning_regime is SitePlanningRegime(regime)
    assert profile.display_name == f"Profil {regime}"
    assert profile.active is True
    assert profile.standard_shifts == []
    assert profile.day_only_blocks_n is True
    assert profile.external_support_enabled is True
    assert profile.training_s_enabled is False
    assert profile.training_s_weekdays_only is False
    assert profile.training_s_default_readiness_threshold == 1
    assert profile.rolling_7d_decision_threshold_hours == 40
    assert [(a.coordinator_id, a.site_id, a.active) for a in associations] == [
        (DEV_COORDINATOR_ID, created.site_id, True)
    ]
    assert len(summaries) == 1
    assert summaries[0].planning_regime == regime
    assert summaries[0].complete is False
    assert summaries[0].print_settings_missing is True


def test_calendar_bulk_fills_only_gaps_and_preserves_both_saved_states(conn):
    created = _create(conn)
    set_day(SetDayRequest(date="2026-08-02", holiday=True, site_id=created.site_id), conn)
    set_day(SetDayRequest(date="2026-08-03", holiday=False, site_id=created.site_id), conn)

    bulk_generate(
        BulkGenerateRequest(start="2026-08-01", end="2026-08-04", site_id=created.site_id),
        conn,
    )

    observed = {row.date: row.holiday for row in get_range("2026-08-01", "2026-08-04", conn)}
    assert observed == {
        "2026-08-01": False,
        "2026-08-02": True,
        "2026-08-03": False,
        "2026-08-04": False,
    }


def test_real_http_routes_persist_through_the_application_to_sqlite(tmp_path):
    database_path = tmp_path / "t021-r5-http.db"
    setup_conn = connect(database_path)
    save_coordinator(setup_conn, Coordinator(DEV_COORDINATOR_ID, "Audytor", True))
    setup_conn.close()

    def override_conn():
        request_conn = connect(database_path)
        try:
            yield request_conn
        finally:
            request_conn.close()

    app.dependency_overrides[api_get_conn] = override_conn
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/workspace/sites",
                json={
                    "display_name": "Obiekt HTTP",
                    "profile_display_name": "Profil HTTP",
                    "rolling_7d_decision_threshold_hours": 40,
                    "planning_regime": "OCHRONA",
                },
            )
            assert created.status_code == 201
            site_id = created.json()["site_id"]

            listed = client.get("/api/workspace/sites")
            assert listed.status_code == 200
            assert [(row["site_id"], row["planning_regime"]) for row in listed.json()] == [
                (site_id, "OCHRONA")
            ]

            assert client.post(
                "/api/workspace/calendar/day",
                json={"date": "2026-08-02", "holiday": True, "site_id": site_id},
            ).status_code == 204
            assert client.post(
                "/api/workspace/calendar/bulk-generate",
                json={"start": "2026-08-01", "end": "2026-08-03", "site_id": site_id},
            ).status_code == 204
            calendar = client.get(
                "/api/workspace/calendar?start=2026-08-01&end=2026-08-03"
            )
            assert calendar.status_code == 200
            assert calendar.json() == [
                {"date": "2026-08-01", "holiday": False},
                {"date": "2026-08-02", "holiday": True},
                {"date": "2026-08-03", "holiday": False},
            ]

            for route in ("backup", "diagnostics"):
                download = client.post(f"/api/workspace/{route}")
                assert download.status_code == 200
                assert download.content
                assert "filename=" in download.headers["content-disposition"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "invoke",
    [
        lambda conn, site_id: get_range("not-a-date", "2026-08-31", conn),
        lambda conn, site_id: bulk_generate(
            BulkGenerateRequest(start="not-a-date", end="2026-08-31", site_id=site_id), conn
        ),
        lambda conn, site_id: set_day(
            SetDayRequest(date="not-a-date", holiday=False, site_id=site_id), conn
        ),
    ],
)
def test_every_calendar_route_uses_shared_value_error_mapping(conn, invoke):
    created = _create(conn)
    with pytest.raises(HTTPException) as raised:
        invoke(conn, created.site_id)
    assert raised.value.status_code == 400


def test_site_list_uses_shared_print_settings_error_mapping(conn, monkeypatch):
    _create(conn)

    def invalid_settings(*_args, **_kwargs):
        raise InvalidSitePrintSettings("corrupt print settings")

    monkeypatch.setattr(bootstrap_router, "get_site_print_settings", invalid_settings)
    with pytest.raises(HTTPException) as raised:
        list_sites(conn)
    assert raised.value.status_code == 422


def test_durable_inputs_router_keeps_the_wrapped_application_owner():
    for application_function in (
        durable_inputs_router.set_calendar_day,
        durable_inputs_router.fill_missing_calendar_days,
    ):
        application_module = inspect.getmodule(application_function)
        assert application_module is not None
        assert durable_inputs_router.__name__.split(".")[-1] == application_module.__name__.split(".")[-1]


def test_t021_does_not_modify_the_existing_rota_layer():
    result = subprocess.run(
        ["git", "diff", "--name-only", ACCEPTED_CONTRACT_SHA, "HEAD", "--", "rota"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "", (
        "brief.md section 6 makes existing rota/** read-only for T021; "
        f"changed paths:\n{result.stdout}"
    )


@pytest.mark.parametrize(
    ("backend_message", "english_fragment"),
    [
        ("coordinator 'COORD-1' is not active", "is not active"),
        ("coordinator 'COORD-1' does not exist", "does not exist"),
        ("site 'SITE-1' is not active", "is not active"),
        ("site profile 'PROF-1' is not active", "is not active"),
        ("site profile 'PROF-1' has no valid standard shift", "no valid standard shift"),
        ("site 'SITE-1' does not exist", "does not exist"),
        (
            "no active CoordinatorSiteAssociation for ('COORD-1', 'SITE-1')",
            "no active CoordinatorSiteAssociation",
        ),
        ("site 'SITE-1' has no active LOCAL SiteMembership", "no active LOCAL SiteMembership"),
    ],
)
def test_workspace_does_not_render_reachable_backend_english_missing_text(
    backend_message, english_fragment
):
    workspace_path = REPO_ROOT / "frontend/src/screens/Workspace.tsx"
    esbuild_path = REPO_ROOT / "frontend/node_modules/esbuild"
    source_suffix = f"""
import {{ renderToStaticMarkup }} from "react-dom/server";
const auditSite = {{
  site_id: "SITE-1",
  display_name: "Obiekt",
  planning_regime: "OCHRONA",
  complete: false,
  missing: [{json.dumps(backend_message)}],
  decision_required_months: [],
  print_settings_missing: false,
}};
console.log(renderToStaticMarkup(<SiteRow site={{auditSite}} />));
"""
    harness = f"""
const fs = require("fs");
const esbuild = require({json.dumps(str(esbuild_path))});
const source = fs.readFileSync({json.dumps(str(workspace_path))}, "utf8") + {json.dumps(source_suffix)};
const result = esbuild.buildSync({{
  stdin: {{
    contents: source,
    resolveDir: {json.dumps(str(workspace_path.parent))},
    sourcefile: "Workspace.audit.tsx",
    loader: "tsx",
  }},
  bundle: true,
  platform: "node",
  format: "cjs",
  jsx: "automatic",
  write: false,
}});
eval(result.outputFiles[0].text);
"""
    result = subprocess.run(
        ["node", "-e", harness], check=False, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert english_fragment not in result.stdout


@pytest.mark.parametrize(
    ("year", "month_index", "day", "expected"),
    [
        (2026, 0, 1, "2026-01-01"),
        (2026, 7, 1, "2026-08-01"),
        (2026, 11, 31, "2026-12-31"),
    ],
)
def test_displayed_polish_calendar_day_is_sent_as_the_same_iso_date(
    year, month_index, day, expected
):
    source = (REPO_ROOT / "frontend/src/screens/Workspace.tsx").read_text(encoding="utf-8")
    match = re.search(r"const iso = \(d: Date\) => (.+);", source)
    assert match, "Workspace must expose one auditable date serializer"
    expression = match.group(1)
    script = (
        f"const iso=(d)=>{expression};"
        f"console.log(JSON.stringify(iso(new Date({year},{month_index},{day}))));"
    )
    env = os.environ.copy()
    env["TZ"] = "Europe/Warsaw"
    result = subprocess.run(
        ["node", "-e", script], check=True, capture_output=True, text=True, env=env
    )
    assert json.loads(result.stdout) == expected
