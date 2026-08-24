from __future__ import annotations

import inspect
import json
import os
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn as api_get_conn
from api.main import app
from api.routers import durable_inputs as durable_inputs_router
from rota.domain import Coordinator
from rota.persistence.coordinator_repository import save_coordinator
from rota.persistence.db import connect


REPO_ROOT = Path(__file__).resolve().parents[4]
ACCEPTED_CONTRACT_SHA = "680a34258f956df26ac6fd9b3190ad4e70c312b0"


def test_t021_keeps_the_existing_rota_layer_read_only():
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


def test_calendar_write_router_is_a_single_day_passthrough_to_its_owner():
    application_module = inspect.getmodule(durable_inputs_router.set_calendar_day)
    assert application_module is not None
    assert durable_inputs_router.__name__.split(".")[-1] == application_module.__name__.split(".")[-1]

    paths = {route.path for route in durable_inputs_router.router.routes}
    assert paths == {"/workspace/calendar/day"}
    assert not hasattr(durable_inputs_router, "fill_missing_calendar_days")


def test_frontend_bulk_action_calls_one_single_day_write_per_missing_date_only():
    workspace_path = REPO_ROOT / "frontend/src/screens/Workspace.tsx"
    esbuild_path = REPO_ROOT / "frontend/node_modules/esbuild"
    source = workspace_path.read_text(encoding="utf-8")

    # Execute the real CalendarModal closure with controlled React hooks and
    # API doubles. The month is pinned only in the audit copy of the source.
    source = source.replace('import { useEffect, useMemo, useState } from "react";', "")
    source = source.replace(
        'import { api, CalendarDayOut, SiteSummary } from "../api/client";', ""
    )
    source = source.replace(
        'import { translateMissingReason } from "../api/completeness";', ""
    )
    source = source.replace(
        "const today = new Date();", "const today = new Date(2026, 7, 23);"
    )
    source += """

globalThis.__auditPromise = (async () => {
  const auditTree = CalendarModal({ siteIdForAuth: "SITE-1", onClose: () => {} });
  const findGenerate = (node) => {
    if (!node || typeof node !== "object") return undefined;
    if (node.props?.className === "btn-secondary") return node;
    const children = node.props?.children;
    for (const child of Array.isArray(children) ? children : [children]) {
      const found = findGenerate(child);
      if (found) return found;
    }
    return undefined;
  };
  const generateButton = findGenerate(auditTree);
  if (!generateButton) throw new Error("calendar generate action not found");
  await generateButton.props.onClick();
  console.log(JSON.stringify(globalThis.__auditCalls));
})();
"""

    harness = f"""
const esbuild = require({json.dumps(str(esbuild_path))});
globalThis.__auditCalls = [];
const existingDays = new Map([
  ["2026-08-02", true],
  ["2026-08-03", false],
]);
let stateCall = 0;
const useState = (initial) => {{
  stateCall += 1;
  if (stateCall === 1) return [existingDays, () => {{}}];
  return [typeof initial === "function" ? initial() : initial, () => {{}}];
}};
const useEffect = () => {{}};
const useMemo = (factory) => factory();
const translateMissingReason = (reason) => reason;
const api = {{
  setCalendarDay: async (date, holiday, siteId) => {{
    globalThis.__auditCalls.push([date, holiday, siteId]);
  }},
  getCalendarRange: async () => [],
}};
const __jsx = (type, props, ...children) => ({{
  type,
  props: {{ ...(props ?? {{}}), children: children.length <= 1 ? children[0] : children }},
}});
(async () => {{
  const transformed = esbuild.transformSync({json.dumps(source)}, {{
    loader: "tsx",
    format: "cjs",
    target: "es2022",
    jsx: "transform",
    jsxFactory: "__jsx",
  }});
  eval(transformed.code);
  await globalThis.__auditPromise;
}})().catch((error) => {{ console.error(error); process.exitCode = 1; }});
"""
    result = subprocess.run(
        ["node", "-e", harness],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "TZ": "Europe/Warsaw"},
    )
    assert result.returncode == 0, result.stderr

    calls = json.loads(result.stdout)
    expected_dates = [
        f"2026-08-{day:02d}" for day in range(1, 32) if day not in {2, 3}
    ]
    assert calls == [[day, False, "SITE-1"] for day in expected_dates]


def test_real_http_vertical_keeps_saved_calendar_states_and_has_no_bulk_route(tmp_path):
    database_path = tmp_path / "t021-r6-http.db"
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

            for day, holiday in (("2026-08-02", True), ("2026-08-03", False)):
                response = client.post(
                    "/api/workspace/calendar/day",
                    json={"date": day, "holiday": holiday, "site_id": site_id},
                )
                assert response.status_code == 204

            calendar = client.get(
                "/api/workspace/calendar?start=2026-08-01&end=2026-08-04"
            )
            assert calendar.status_code == 200
            assert calendar.json() == [
                {"date": "2026-08-02", "holiday": True},
                {"date": "2026-08-03", "holiday": False},
            ]
            assert client.post(
                "/api/workspace/calendar/bulk-generate",
                json={"start": "2026-08-01", "end": "2026-08-04", "site_id": site_id},
            ).status_code == 404
    finally:
        app.dependency_overrides.clear()
