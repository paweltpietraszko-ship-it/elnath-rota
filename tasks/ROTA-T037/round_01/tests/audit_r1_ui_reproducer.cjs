/* Independent T037 UI reproducer with API responses fixed at the audited seam. */
const { chromium } = require("../../../../frontend/node_modules/@playwright/test");

(async () => {
  let nn = false;
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    args: ["--no-proxy-server"],
  });
  const page = await browser.newPage();
  page.on("pageerror", (error) => console.error(`PAGEERROR: ${error.message}`));
  page.on("response", (response) => {
    if (response.status() >= 400) console.error(`HTTP ${response.status()}: ${response.url()}`);
  });
  page.on("console", (message) => {
    if (message.type() === "error") console.error(`CONSOLE: ${message.text()}`);
  });
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (!path.startsWith("/api/")) return route.continue();
    if (path === "/api/workspace/sites") {
      return route.fulfill({
        json: [{
          site_id: "SITE-1", display_name: "Obiekt testowy", planning_regime: "OCHRONA",
          complete: true, missing: [], decision_required_months: [], print_settings_missing: false, active: true,
        }],
      });
    }
    if (path.endsWith("/roster")) {
      return route.fulfill({
        json: [
          { employee_id: "E1", display_name: "Anna", enabled: true, can_work_24h: false,
            readiness_state: "READY_FOR_PRIMARY", membership_kind: "LOCAL" },
          { employee_id: "E2", display_name: "Beata", enabled: true, can_work_24h: false,
            readiness_state: "READY_FOR_PRIMARY", membership_kind: "LOCAL" },
        ],
      });
    }
    if (path.endsWith("/schedule/months")) {
      return route.fulfill({ json: { months: ["2026-08-01"] } });
    }
    if (path.endsWith("/print-settings")) {
      return route.fulfill({ json: null });
    }
    if (path.endsWith("/manual-correction/mark-not-worked")) {
      nn = true;
      return route.fulfill({
        json: {
          version_id: "SV-2", status: "WORKING_WITH_DEVIATIONS",
          deviations: [{
            deviation_id: "DEV-1", category: "COVERAGE", source_reference: "COVERAGE-01",
            label: "brak pokrycia zmiany", affected_assignment_or_employee: "D1", acknowledged: false,
          }],
        },
      });
    }
    if (/\/schedule\/\d{4}-\d{2}-01$/.test(path)) {
      const version = nn ? "SV-2" : "SV-1";
      return route.fulfill({
        json: {
          current_version: {
            version_id: version, status: nn ? "WORKING_WITH_DEVIATIONS" : "WORKING",
            effective_from: "2026-08-01", created_at: "2026-08-01T00:00:00",
            created_by: "COORD", parent_version_id: nn ? "SV-1" : null,
          },
          version_history: [],
          demands: [{
            demand_id: "D1", start_datetime: "2026-08-01T06:00:00", end_datetime: "2026-08-01T18:00:00",
            required_primary_count: 1, shift_kind: "D",
          }],
          assignments: [{
            assignment_id: "A1", schedule_version_id: version, employee_id: "E1", employee_display_name: "Anna",
            start_datetime: "2026-08-01T06:00:00", end_datetime: "2026-08-01T18:00:00",
            role: "PRIMARY", state: nn ? "CANCELLED" : "PLANNED", frozen: false, covers_demand_id: "D1",
            mentor_primary_assignment_id: null, operational_code: nn ? "NN" : null,
            work_period_id: "WP-1", required_rest_after_hours: 11,
          }],
          deviations: nn ? [{
            deviation_id: "DEV-1", category: "COVERAGE", source_reference: "COVERAGE-01",
            label: "brak pokrycia zmiany", affected_assignment_or_employee: "D1", acknowledged: false,
          }] : [],
          decision_required: null,
          warnings: [],
        },
      });
    }
    return route.fulfill({ status: 404, json: { detail: `mock missing ${path}` } });
  });

  await page.goto("http://127.0.0.1:4173/");
  await page.waitForTimeout(1000);
  if (await page.locator("[data-diag-action=site-row-open]").count() === 0) {
    console.error(`BODY: ${(await page.locator("body").innerText()).slice(0, 2000)}`);
  }
  await page.locator("[data-diag-action=site-row-open]").click();
  await page.locator("[data-diag-action=room-nav-manual-correction]").click();
  const cell = page.locator("[data-diag-action=manual-correction-select-assignment]").first();
  await cell.waitFor();
  const before = (await cell.innerText()).trim();
  await cell.click();
  await page.getByRole("button", { name: "Nie przepracował (NN)" }).click();
  await page.waitForFunction(() => document.body.innerText.includes("brak pokrycia zmiany"));
  const after = (await page.locator("[data-diag-action=manual-correction-select-assignment]").first().innerText()).trim();
  await page.locator("[data-diag-action=print-toggle]").click();
  await page.getByRole("heading", { name: "Wydruk Grafiku" }).waitFor();
  const body = await page.locator("body").innerText();
  console.log(JSON.stringify({
    before,
    after,
    nnVisibleAfter: body.includes("NN"),
    deviationVisible: body.includes("brak pokrycia zmiany"),
    manualShortcutOpenedPlanning: body.includes("Planowanie miesiąca"),
    embeddedPrintVisible: body.includes("Wydruk Grafiku"),
  }));
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
