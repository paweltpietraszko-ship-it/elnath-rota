import { expect, test } from "@playwright/test";

// ROTA-T062: unblocking_options is now {text, target} instead of a bare
// string Decisions.tsx used to parse by matching Polish text prefixes.
// This verifies the real rendering against both real shapes: a stable
// target (clickable) and no target (plain information).
const site = {
  site_id: "SITE-T062-GUIDANCE", display_name: "Obiekt T062 Guidance", planning_regime: "ORDINARY",
  complete: true, missing: [], decision_required_months: ["2026-10-01"], print_settings_missing: false, active: true,
};

test("T062: opcja ze stabilnym celem jest klikalna, bez celu to zwykły tekst", async ({ page }) => {
  await page.route("**/api/workspace/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = {};
    if (path === "/api/workspace/sites") body = [site];
    else if (path.endsWith("/overview")) body = { decision_months: ["2026-10-01"], version_status: null, resumable: false, headcount: 0 };
    else if (path.endsWith("/decisions/months")) body = { months: ["2026-10-01"] };
    else if (path.endsWith("/decisions/2026-10-01")) {
      body = {
        decision_required_id: "DEC-1", site_id: site.site_id, month: "2026-10-01", schedule_version_id: null,
        requested_by: "COORD", recorded_at: "2026-10-01T08:00:00",
        blocking_shift_demands: [], blockers: [{ employee_id: "EMP-1", condition: "Koliduje z ustawieniem: Ogólna dostępność" }],
        load_blocker: null,
        unblocking_options: [
          { text: "Zmień Ogólna dostępność: Jan Kowalski", target: "obsada" },
          { text: "Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach.", target: null },
        ],
        linked_action_ids: [],
      };
    } else if (path.endsWith("/roster")) body = [{ employee_id: "EMP-1", display_name: "Jan Kowalski", active: true }];
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto("/");
  await page.getByText(site.display_name, { exact: true }).click();
  await page.getByRole("button", { name: "Decyzje koordynatora", exact: true }).click();

  // The stable-target option renders as a real button...
  const link = page.getByRole("button", { name: "Zmień Ogólna dostępność: Jan Kowalski" });
  await expect(link).toBeVisible();
  await link.click();
  await expect(page.getByRole("heading", { name: "Lista pracowników" })).toBeVisible();

  // ...the target-less option never became a button anywhere on the page.
  await expect(
    page.getByRole("button", { name: "Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach." }),
  ).toHaveCount(0);
});
