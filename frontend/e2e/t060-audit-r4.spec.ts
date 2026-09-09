import { expect, test } from "@playwright/test";

const site = {
  site_id: "SITE-INTERNAL-SECRET", display_name: "Obiekt Audyt T060", planning_regime: "ORDINARY",
  complete: true, missing: [], decision_required_months: [], print_settings_missing: false, active: true,
};

test("R4: Historia Przed/Po nie może ujawnić ID prawdziwego Assignmentu", async ({ page }) => {
  await page.route("**/api/workspace/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = {};
    if (path === "/api/workspace/sites") body = [site];
    else if (path.endsWith("/overview")) body = { decision_months: [], version_status: null, resumable: false, headcount: 0 };
    else if (path.endsWith("/roster")) body = [];
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
      before_state: { parent_version_id: "SV-PARENT-SECRET", assignments: [{
        schedule_version_id: "SV-ASSIGNMENT-SECRET", assignment_id: "ASSIGNMENT-SECRET",
        employee_id: "EMPLOYEE-SECRET", covers_demand_id: "DEMAND-SECRET",
        mentor_primary_assignment_id: "MENTOR-SECRET", work_period_id: "WORK-PERIOD-SECRET",
      }] },
      after_state: null,
    };
    else if (path.endsWith("/history/rules")) body = {};
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto("/");
  await page.getByText(site.display_name, { exact: true }).click();
  await page.getByRole("button", { name: "Historia i audyt", exact: true }).click();
  await page.getByRole("button", { name: "Szczegóły" }).click();

  await expect(page.getByText("assignment_id: ASSIGNMENT-SECRET", { exact: true })).toBeVisible();
  await expect(page.getByText("schedule_version_id: SV-ASSIGNMENT-SECRET", { exact: true })).toBeVisible();
  await expect(page.getByText("covers_demand_id: DEMAND-SECRET", { exact: true })).toBeVisible();
});
