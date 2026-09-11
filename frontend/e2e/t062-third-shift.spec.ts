import { expect, test } from "@playwright/test";

// ROTA-T062 (brief section 4 point 6): THIRD_CONSECUTIVE_SHIFT_BLOCKED now
// shares decision_guidance's real, evidence-backed text (naming the actual
// employee) instead of MonthlyPlanning.tsx's own hand-written generic
// banner -- verifies the real text renders, not the old hardcoded string.
const site = {
  site_id: "SITE-T062-THIRD", display_name: "Obiekt T062 Third", planning_regime: "ORDINARY",
  complete: true, missing: [], decision_required_months: [], print_settings_missing: false, active: true,
};

test("T062: baner THIRD pokazuje realny tekst ze wspólnego guidance, nazywa pracownika", async ({ page }) => {
  await page.route("**/api/workspace/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = {};
    if (path === "/api/workspace/sites") body = [site];
    else if (path.endsWith("/overview")) body = { decision_months: [], version_status: null, resumable: false, headcount: 0 };
    else if (path.endsWith("/roster")) body = [];
    else if (/\/schedule\/\d{4}-\d{2}-\d{2}$/.test(path) && route.request().method() === "GET") {
      body = {
        current_version: null, version_history: [], demands: [], assignments: [], deviations: [],
        decision_required: null, warnings: [], plan_preview: null, plan_preview_error: null,
      };
    } else if (path.endsWith("/plan")) {
      body = {
        status: "THIRD_CONSECUTIVE_SHIFT_BLOCKED", candidates: [],
        decision_payload: {
          blocking_shift_demands: [], blockers: [], load_blocker: null,
          unblocking_options: [{ text: "Sprawdź obsadę i dostępność: Jan Kowalski, i zaplanuj ponownie", target: "obsada" }],
        },
        error_message: null, warnings: ["THIRD-CONSECUTIVE-SHIFT-01: ..."], optimization_complete: true,
      };
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto("/");
  await page.getByText(site.display_name, { exact: true }).click();
  await page.getByRole("button", { name: "Planowanie miesiąca", exact: true }).click();
  await page.locator('[data-diag-action="plan-month-first"]').click();

  await expect(page.getByText("Sprawdź obsadę i dostępność: Jan Kowalski, i zaplanuj ponownie")).toBeVisible();
  await expect(page.getByText("THIRD_CONSECUTIVE_SHIFT_BLOCKED")).toHaveCount(0);
});
