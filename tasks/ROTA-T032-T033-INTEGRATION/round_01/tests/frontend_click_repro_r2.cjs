/* Real-browser reproducer: the accepted "Użyj tego grafiku" action must
   invoke the existing select-candidate write, not merely hide its prompt. */
const { chromium } = require("C:/Projects/Elnath Rota/frontend/node_modules/playwright");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  });
  const page = await browser.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(String(error)));
  page.on("requestfailed", (request) => pageErrors.push(`${request.url()}: ${request.failure()?.errorText}`));
  page.on("console", (message) => {
    if (message.type() === "error") pageErrors.push(`console: ${message.text()}`);
  });
  let selectCalls = 0;
  const today = new Date();
  const month = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-01`;
  const site = {
    site_id: "SITE-AUDIT", display_name: "Audit Site", planning_regime: "OCHRONA",
    complete: true, missing: [], decision_required_months: [], print_settings_missing: false, active: true,
  };
  const version = {
    version_id: "SV-CURRENT", status: "WORKING", effective_from: month,
    created_at: `${month}T00:00:00`, created_by: "COORD", parent_version_id: null,
  };
  const monthView = {
    current_version: version, version_history: [version], demands: [], assignments: [], deviations: [],
    decision_required: null, warnings: [],
  };
  const partial = {
    status: "FEASIBLE", candidates: [[]], decision_payload: null, error_message: null,
    warnings: [], optimization_complete: false,
  };

  await page.route("**/api/workspace/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    if (req.method() === "POST" && path.endsWith("/select-candidate")) {
      selectCalls += 1;
      return route.fulfill({ status: 204, body: "" });
    }
    if (req.method() === "POST" && path.endsWith(`/schedule/${month}/plan`)) {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(partial) });
    }
    if (path === "/api/workspace/sites") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([site]) });
    }
    if (path.endsWith("/schedule/months")) {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ months: [month] }) });
    }
    if (path.endsWith(`/schedule/${month}`)) {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(monthView) });
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
    await page.waitForTimeout(250);
    if (await page.getByText("Audit Site", { exact: true }).count() === 0) {
      throw new Error(`mocked site did not render: ${await page.locator("body").innerText()} errors=${pageErrors.join(" | ")}`);
    }
    await page.getByText("Audit Site", { exact: true }).click();
    await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
    await page.locator('[data-diag-action="plan-month-recompute"]').click();
    await page.locator('[data-diag-action="accept-incomplete"]').click();
    await page.waitForTimeout(100);
    if (selectCalls !== 1) {
      throw new Error(`Użyj tego grafiku did not persist the candidate: select-candidate calls=${selectCalls}`);
    }
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
