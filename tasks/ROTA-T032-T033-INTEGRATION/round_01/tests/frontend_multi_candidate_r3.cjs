/* Real-browser sibling check for FEASIBLE+incomplete with >1 candidate. */
const { chromium } = require("C:/Projects/Elnath Rota/frontend/node_modules/playwright");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  });
  const page = await browser.newPage();
  const today = new Date();
  const month = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-01`;
  let selectedEmployee = null;
  const assignment = (employeeId) => ({
    assignment_id: `A-${employeeId}`, schedule_version_id: "SV-CURRENT", employee_id: employeeId,
    employee_display_name: employeeId, start_datetime: `${month}T06:00:00`, end_datetime: `${month}T18:00:00`,
    role: "PRIMARY", state: "PLANNED", frozen: false, covers_demand_id: null,
    mentor_primary_assignment_id: null, operational_code: null, work_period_id: null,
    required_rest_after_hours: null,
  });
  const version = {
    version_id: "SV-CURRENT", status: "WORKING", effective_from: month,
    created_at: `${month}T00:00:00`, created_by: "COORD", parent_version_id: null,
  };

  await page.route("**/api/workspace/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() === "POST" && path.endsWith("/select-candidate")) {
      selectedEmployee = request.postDataJSON().candidate[0].employee_id;
      return route.fulfill({ status: 204, body: "" });
    }
    if (request.method() === "POST" && path.endsWith(`/schedule/${month}/plan`)) {
      return route.fulfill({
        status: 200, contentType: "application/json",
        body: JSON.stringify({
          status: "FEASIBLE", candidates: [[assignment("EMP-A")], [assignment("EMP-B")]],
          decision_payload: null, error_message: null, warnings: [], optimization_complete: false,
        }),
      });
    }
    if (path === "/api/workspace/sites") {
      return route.fulfill({
        status: 200, contentType: "application/json",
        body: JSON.stringify([{
          site_id: "SITE-AUDIT", display_name: "Audit Site", planning_regime: "OCHRONA",
          complete: true, missing: [], decision_required_months: [], print_settings_missing: false, active: true,
        }]),
      });
    }
    if (path.endsWith("/schedule/months")) {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ months: [month] }) });
    }
    if (path.endsWith(`/schedule/${month}`)) {
      return route.fulfill({
        status: 200, contentType: "application/json",
        body: JSON.stringify({
          current_version: version, version_history: [version], demands: [], assignments: [], deviations: [],
          decision_required: null, warnings: [],
        }),
      });
    }
    if (path.endsWith("/shift-catalog")) {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ shifts: [] }) });
    }
    if (path.endsWith("/roster") || path.endsWith("/roster/pickable")) {
      return route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });

  try {
    await page.goto("http://localhost:5173");
    await page.getByText("Audit Site", { exact: true }).click();
    await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
    await page.locator('[data-diag-action="plan-month-recompute"]').click();
    await page.locator('[data-diag-action="select-candidate"]').first().waitFor();
    if (await page.locator('[data-diag-action="accept-incomplete"]').count()) {
      throw new Error("ambiguous global accept button is visible for multiple candidates");
    }
    const candidateButtons = page.locator('[data-diag-action="select-candidate"]');
    if (await candidateButtons.count() !== 2) throw new Error("expected two candidate-specific actions");
    await candidateButtons.nth(1).click();
    if (selectedEmployee !== "EMP-B") {
      throw new Error(`wrong candidate persisted: ${selectedEmployee}`);
    }
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
