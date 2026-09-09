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
});
