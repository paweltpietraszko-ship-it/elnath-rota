import { expect, test } from "@playwright/test";

// ROTA-T060 Codex R4 audit (tasks/ROTA-T060/round_01/tests/tests_r4.txt):
// the first ID_ONLY_STATE_KEYS list in History.tsx was hand-picked and
// missed the actual keys real writers produce. This regression test uses
// the REAL dict shapes from every producer that can reach this screen's
// action trail -- manual_edit.py::_assignment_state, plan_ops.py::
// _assignment_fact (both identical), manual_edit.py's parent/child wrapper,
// and lifecycle_ops.py::_deviation_fact -- and asserts none of their raw
// technical-id values ever reach the DOM, while employee_id still resolves
// to a real name (never a raw id, never silently dropped).
const site = {
  site_id: "SITE-INTERNAL-SECRET", display_name: "Obiekt Audyt T060 Regresja", planning_regime: "ORDINARY",
  complete: true, missing: [], decision_required_months: [], print_settings_missing: false, active: true,
};

const roster = [{ employee_id: "EMPLOYEE-SECRET", display_name: "Jan Kowalski", active: true }];

test("T060 R4 regresja: Historia redaguje pełny zestaw technicznych ID z Assignmentu i Deviation", async ({ page }) => {
  await page.route("**/api/workspace/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = {};
    if (path === "/api/workspace/sites") body = [site];
    else if (path.endsWith("/overview")) body = { decision_months: [], version_status: null, resumable: false, headcount: 0 };
    else if (path.endsWith("/roster")) body = roster;
    else if (path.endsWith("/history/actions")) body = [{
      action_id: "ACTION-SECRET", action_kind: "MANUAL_SCHEDULE_CORRECTION", origin_site_id: site.site_id,
      affected_site_ids: [site.site_id], coordinator_id: "COORD-SECRET", recorded_at: "2026-09-09T12:00:00",
      effective_from: "2026-09-09", month: "2026-09-01", schedule_version_id: "SV-SUMMARY-SECRET",
      affected_entities: [], note: null, responds_to_decision_required_id: null,
    }];
    else if (path.endsWith("/history/actions/ACTION-SECRET")) body = {
      action_id: "ACTION-SECRET", action_kind: "MANUAL_SCHEDULE_CORRECTION", origin_site_id: site.site_id,
      affected_site_ids: [site.site_id], coordinator_id: "COORD-SECRET", recorded_at: "2026-09-09T12:00:00",
      effective_from: "2026-09-09", month: "2026-09-01", schedule_version_id: "SV-SUMMARY-SECRET",
      affected_entities: [], note: null, responds_to_decision_required_id: null,
      source_kind: "SCHEDULE_VERSION", source_id: "SV-SOURCE-SECRET", responds_to: null,
      // manual_edit.py::_persist_child_and_record_action wrapper + _assignment_state
      before_state: {
        parent_version_id: "SV-PARENT-SECRET",
        assignments: [{
          schedule_version_id: "SV-ASSIGNMENT-SECRET", assignment_id: "ASSIGNMENT-SECRET",
          employee_id: "EMPLOYEE-SECRET", covers_demand_id: "DEMAND-SECRET",
          mentor_primary_assignment_id: "MENTOR-SECRET", work_period_id: "WORK-PERIOD-SECRET",
        }],
      },
      // plan_ops.py::_candidate_delta shape + lifecycle_ops.py::_deviation_fact
      after_state: {
        child_version_id: "SV-CHILD-SECRET",
        added: [{
          schedule_version_id: "SV-CANDIDATE-SECRET", assignment_id: "CANDIDATE-ASSIGNMENT-SECRET",
          employee_id: "EMPLOYEE-SECRET", covers_demand_id: "CANDIDATE-DEMAND-SECRET",
          mentor_primary_assignment_id: "CANDIDATE-MENTOR-SECRET", work_period_id: "CANDIDATE-WORK-PERIOD-SECRET",
        }],
        deviations: [{
          deviation_id: "DEV-SECRET", category: "OPERATIONAL", source_reference: "REST-01",
          affected_assignment_or_employee: "AFFECTED-SECRET", acknowledged: true,
          acknowledged_by: "COORD-ACK-SECRET", acknowledged_at: "2026-09-09T12:00:00", reason: null,
        }],
      },
    };
    else if (path.endsWith("/history/rules")) body = {};
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto("/");
  await page.getByText(site.display_name, { exact: true }).click();
  await page.getByRole("button", { name: "Historia i audyt", exact: true }).click();
  await page.getByRole("button", { name: "Szczegóły" }).click();

  const bodyText = await page.locator("body").innerText();
  for (const secret of [
    "SV-PARENT-SECRET", "SV-ASSIGNMENT-SECRET", "ASSIGNMENT-SECRET", "DEMAND-SECRET",
    "MENTOR-SECRET", "WORK-PERIOD-SECRET", "SV-CHILD-SECRET", "SV-CANDIDATE-SECRET",
    "CANDIDATE-ASSIGNMENT-SECRET", "CANDIDATE-DEMAND-SECRET", "CANDIDATE-MENTOR-SECRET",
    "CANDIDATE-WORK-PERIOD-SECRET", "DEV-SECRET", "AFFECTED-SECRET", "COORD-ACK-SECRET",
  ]) {
    expect(bodyText).not.toContain(secret);
  }

  // employee_id must resolve to the real roster name, never the raw id and
  // never silently dropped.
  await expect(page.getByText("Jan Kowalski").first()).toBeVisible();
  await expect(page.getByText("EMPLOYEE-SECRET")).toHaveCount(0);

  // Codex R5 audit (tasts_r5.txt): redacting the VALUE isn't enough when the
  // KEY itself is still the raw English technical name -- assert none of
  // the newly-added ID_ONLY_STATE_KEYS leak their own key name either.
  for (const rawKey of [
    "assignment_id", "schedule_version_id", "covers_demand_id", "mentor_primary_assignment_id",
    "work_period_id", "parent_version_id", "child_version_id", "deviation_id", "source_reference",
    "affected_assignment_or_employee", "acknowledged_by",
  ]) {
    expect(bodyText).not.toContain(rawKey);
  }
});

// Codex R5 audit (tasks/ROTA-T060/round_01/tests/tests_r5.txt): the "Reguły"
// tab has its own, independent leak path -- manual_edit.py::
// _rest_override_rule_content builds `rule_id = f"REST-OVERRIDE:{child_id}"`
// and an English `statement` embedding that same child_id plus raw
// employee_ids. Backend data/semantics are untouched by this fix (Codex:
// "naprawa należy do prezentacji Historii") -- only History.tsx's RulesTab
// presentation of an already-fetched DecisionRecordOut changes.
test("T060 R5 regresja: zakładka Reguły nie ujawnia id grafiku ani pracownika z REST OVERRIDE", async ({ page }) => {
  const site2 = {
    site_id: "SITE-INTERNAL-SECRET", display_name: "Obiekt Audyt T060 Reguly", planning_regime: "ORDINARY",
    complete: true, missing: [], decision_required_months: [], print_settings_missing: false, active: true,
  };
  const roster2 = [{ employee_id: "EMPLOYEE-SECRET", display_name: "Jan Kowalski", active: true }];

  await page.route("**/api/workspace/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = {};
    if (path === "/api/workspace/sites") body = [site2];
    else if (path.endsWith("/overview")) body = { decision_months: [], version_status: null, resumable: false, headcount: 0 };
    else if (path.endsWith("/roster")) body = roster2;
    else if (path.endsWith("/history/actions")) body = [];
    else if (path.endsWith("/history/rules")) body = {
      "REST-OVERRIDE:SV-RULE-SECRET": [{
        decision_id: "DECISION-SECRET", site_id: site2.site_id,
        rule_id: "REST-OVERRIDE:SV-RULE-SECRET", chain_seq: 1,
        statement: "Manual correction SV-RULE-SECRET knowingly overrides REST-01 for 1 pair(s), employees EMPLOYEE-SECRET.",
        coordinator_id: "COORD-SECRET", recorded_at: "2026-09-09T12:00:00",
        effective_from: "2026-09-09", rule_version_id: null, rel: null, predecessor_decision_id: null,
      }],
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto("/");
  await page.getByText(site2.display_name, { exact: true }).click();
  await page.getByRole("button", { name: "Historia i audyt", exact: true }).click();
  await page.getByRole("button", { name: "Reguły", exact: true }).click();
  await expect(page.getByText("Wyjątek odpoczynku (korekta ręczna)")).toBeVisible();

  const bodyText = await page.locator("body").innerText();
  expect(bodyText).not.toContain("SV-RULE-SECRET");
  expect(bodyText).not.toContain("EMPLOYEE-SECRET");
  expect(bodyText).toContain("Manual correction");
  await expect(page.getByText("Jan Kowalski")).toBeVisible();
});
