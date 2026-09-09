import { expect, test } from "@playwright/test";

const site = {
  site_id: "SITE-INTERNAL-SECRET", display_name: "Obiekt Audyt T060 R6", planning_regime: "ORDINARY",
  complete: true, missing: [], decision_required_months: [], print_settings_missing: false, active: true,
};
const matrixRuleId = "R-EMP-MATRIX-0123456789abcdef0123456789abcdef";

async function openRules(page: import("@playwright/test").Page) {
  await page.route("**/api/workspace/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = {};
    if (path === "/api/workspace/sites") body = [site];
    else if (path.endsWith("/overview")) body = { decision_months: [], version_status: null, resumable: false, headcount: 0 };
    else if (path.endsWith("/roster")) body = [{
      employee_id: "EMPLOYEE-SECRET", display_name: "Jan Kowalski", enabled: true,
      can_work_24h: false, readiness_state: "READY", membership_kind: "LOCAL",
    }];
    else if (path.endsWith("/history/actions")) body = [];
    else if (path.endsWith("/history/rules")) body = {
      "REST-OVERRIDE:SV-RULE-SECRET": [{
        decision_id: "DECISION-REST", site_id: site.site_id, rule_id: "REST-OVERRIDE:SV-RULE-SECRET", chain_seq: 1,
        statement: "Manual correction SV-RULE-SECRET knowingly overrides REST-01 for 1 pair(s), employees EMPLOYEE-SECRET.",
        coordinator_id: "COORD-SECRET", recorded_at: "2026-09-09T12:00:00", effective_from: "2026-09-09",
        rule_version_id: null, rel: null, predecessor_decision_id: null,
      }],
      [matrixRuleId]: [{
        decision_id: "DECISION-MATRIX", site_id: site.site_id, rule_id: matrixRuleId, chain_seq: 1,
        statement: "Dniówka: niedostępna od 09.09.2026, bezterminowo",
        coordinator_id: "COORD-SECRET", recorded_at: "2026-09-09T13:00:00", effective_from: "2026-09-09",
        rule_version_id: "RULE-VERSION-SECRET", rel: null, predecessor_decision_id: null,
      }],
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto("/");
  await page.getByText(site.display_name, { exact: true }).click();
  await page.getByRole("button", { name: "Historia i audyt", exact: true }).click();
  await page.getByRole("button", { name: "Reguły", exact: true }).click();
}

test("R6: REST OVERRIDE ma czytelny opis zamiast surowego komunikatu technicznego", async ({ page }) => {
  await openRules(page);
  await expect(page.getByText("Wyjątek odpoczynku (korekta ręczna)")).toBeVisible();
  await expect(page.locator("body")).not.toContainText("Manual correction");
  await expect(page.locator("body")).not.toContainText("REST-01");
});

test("R6: rzeczywista reguła macierzy nie pokazuje technicznego rule_id", async ({ page }) => {
  await openRules(page);
  await expect(page.getByText("Dniówka: niedostępna od 09.09.2026, bezterminowo")).toBeVisible();
  await expect(page.locator("body")).not.toContainText(matrixRuleId);
});
