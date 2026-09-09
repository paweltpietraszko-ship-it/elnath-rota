import { expect, test } from "@playwright/test";

const site = {
  site_id: "SITE-INTERNAL-SECRET", display_name: "Obiekt Audyt T060 R5", planning_regime: "ORDINARY",
  complete: true, missing: [], decision_required_months: [], print_settings_missing: false, active: true,
};

const roster = [{
  employee_id: "EMPLOYEE-SECRET", display_name: "Jan Kowalski", enabled: true,
  can_work_24h: false, readiness_state: "READY", membership_kind: "LOCAL",
}];

async function mockHistory(page: import("@playwright/test").Page) {
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
      before_state: { assignments: [{
        schedule_version_id: "SV-ASSIGNMENT-SECRET", assignment_id: "ASSIGNMENT-SECRET",
        employee_id: "EMPLOYEE-SECRET", covers_demand_id: "DEMAND-SECRET",
      }] },
      after_state: { deviations: [{
        deviation_id: "DEV-SECRET", source_reference: "REST-01",
        affected_assignment_or_employee: "AFFECTED-SECRET", acknowledged_by: "COORD-ACK-SECRET",
      }] },
    };
    else if (path.endsWith("/history/rules")) body = {
      "REST-OVERRIDE:SV-RULE-SECRET": [{
        decision_id: "DECISION-SECRET", site_id: site.site_id,
        rule_id: "REST-OVERRIDE:SV-RULE-SECRET", chain_seq: 1,
        statement: "Manual correction SV-RULE-SECRET knowingly overrides REST-01 for 1 pair(s), employees EMPLOYEE-SECRET.",
        coordinator_id: "COORD-SECRET", recorded_at: "2026-09-09T12:00:00",
        effective_from: "2026-09-09", rule_version_id: null, rel: null, predecessor_decision_id: null,
      }],
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
}

async function openHistory(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByText(site.display_name, { exact: true }).click();
  await page.getByRole("button", { name: "Historia i audyt", exact: true }).click();
}

test("R5: wartości ID są ukryte, ale techniczne nazwy pól nie mogą zostać etykietami", async ({ page }) => {
  await mockHistory(page);
  await openHistory(page);
  await page.getByRole("button", { name: "Szczegóły" }).click();

  const body = page.locator("body");
  await expect(body).not.toContainText("ASSIGNMENT-SECRET");
  await expect(body).not.toContainText("DEV-SECRET");
  await expect(body).not.toContainText("assignment_id");
  await expect(body).not.toContainText("deviation_id");
});

test("R5: zakładka Reguły nie może wyświetlać technicznych ID z ręcznego odstępstwa", async ({ page }) => {
  await mockHistory(page);
  await openHistory(page);
  await page.getByRole("button", { name: "Reguły", exact: true }).click();

  const body = page.locator("body");
  await expect(body).toContainText("Manual correction");
  await expect(body).not.toContainText("SV-RULE-SECRET");
  await expect(body).not.toContainText("EMPLOYEE-SECRET");
});
