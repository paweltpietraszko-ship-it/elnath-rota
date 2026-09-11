import { expect, test } from "@playwright/test";

const site = {
  site_id: "SITE-PLAN-UNKNOWN-AUDIT",
  display_name: "Obiekt testowy czasu wyszukiwania",
  planning_regime: "ORDINARY",
  complete: true,
  missing: [],
  decision_required_months: [],
  print_settings_missing: false,
  active: true,
};

const incomplete = {
  status: "SEARCH_INCOMPLETE",
  candidates: [],
  decision_payload: null,
  error_message: null,
  warnings: [],
  optimization_complete: false,
};

async function installApi(page: import("@playwright/test").Page, requests: Array<{ path: string; body: unknown }>) {
  await page.route("**/api/workspace/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    let body: unknown = {};
    if (path === "/api/workspace/sites") body = [site];
    else if (path.endsWith("/overview")) body = { decision_months: [], version_status: null, resumable: false, headcount: 0 };
    else if (path.endsWith("/roster")) body = [];
    else if (/\/schedule\/\d{4}-\d{2}-\d{2}$/.test(path) && request.method() === "GET") {
      body = {
        current_version: null,
        version_history: [],
        demands: [],
        assignments: [],
        deviations: [],
        decision_required: null,
        warnings: [],
        plan_preview: null,
        plan_preview_error: null,
      };
    } else if (request.method() === "POST" && (path.endsWith("/plan") || path.endsWith("/replan") || path.endsWith("/replan/retry"))) {
      requests.push({ path, body: request.postDataJSON() });
      body = incomplete;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
}

async function openPlanning(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByText(site.display_name, { exact: true }).click();
  await page.getByRole("button", { name: "Planowanie miesiąca", exact: true }).click();
}

test("PLAN bez wyniku pokazuje prosty komunikat i ponawia PLAN z kolejną próbą", async ({ page }, testInfo) => {
  const requests: Array<{ path: string; body: unknown }> = [];
  await installApi(page, requests);
  await openPlanning(page);

  await page.locator('[data-diag-action="plan-month-first"]').click();
  await expect(page.getByText("Program nie zdążył ułożyć grafiku w dostępnym czasie. Możesz ponowić wyszukiwanie.")).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("plan-search-incomplete.png"), fullPage: true });

  await page.locator('[data-diag-action="replan-retry-incomplete"]').click();
  await expect.poll(() => requests.filter((entry) => entry.path.endsWith("/plan")).length).toBe(2);
  const planRequests = requests.filter((entry) => entry.path.endsWith("/plan"));
  expect(planRequests[1].body).toMatchObject({ search_attempt: 1 });
  expect(requests.some((entry) => entry.path.endsWith("/replan/retry"))).toBe(false);
  await expect(page.getByText("Program nie zdążył ułożyć grafiku w dostępnym czasie. Możesz ponowić wyszukiwanie.")).toBeVisible();
});

test("REPLAN bez wyniku nadal ponawia istniejącą ścieżkę REPLAN", async ({ page }) => {
  const requests: Array<{ path: string; body: unknown }> = [];
  await installApi(page, requests);
  await openPlanning(page);

  await page.locator('[data-diag-action="replan-fresh"]').click();
  await expect(page.getByText("Program nie zdążył ułożyć grafiku w dostępnym czasie. Możesz ponowić wyszukiwanie.")).toBeVisible();
  await page.locator('[data-diag-action="replan-retry-incomplete"]').click();

  await expect.poll(() => requests.filter((entry) => entry.path.endsWith("/replan/retry")).length).toBe(1);
  expect(requests.filter((entry) => entry.path.endsWith("/plan"))).toHaveLength(0);
  await expect(page.getByText("Program nie zdążył ułożyć grafiku w dostępnym czasie. Możesz ponowić wyszukiwanie.")).toBeVisible();
});

test("PLAN po zapisanym podglądzie nie gubi komunikatu, gdy dalsze szukanie nie zdąży", async ({ page }, testInfo) => {
  let previewExists = true;
  await page.route("**/api/workspace/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    let body: unknown = {};
    if (path === "/api/workspace/sites") body = [site];
    else if (path.endsWith("/overview")) body = { decision_months: [], version_status: null, resumable: false, headcount: 0 };
    else if (path.endsWith("/roster")) body = [];
    else if (/\/schedule\/\d{4}-\d{2}-\d{2}$/.test(path) && request.method() === "GET") {
      body = {
        current_version: null,
        version_history: [],
        demands: [],
        assignments: [],
        deviations: [],
        decision_required: null,
        warnings: [],
        plan_preview: previewExists ? {
          schedule_version_id: "",
          candidates: [[]],
          warnings: [],
          optimization_complete: false,
          operation_kind: "plan",
        } : null,
        plan_preview_error: null,
      };
    } else if (request.method() === "POST" && path.endsWith("/plan")) {
      previewExists = false;
      body = incomplete;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await openPlanning(page);
  const searchAgain = page.locator('[data-diag-action="search-again-incomplete"]');
  await expect(searchAgain).toBeVisible();
  page.on("dialog", async (dialog) => dialog.accept());
  await searchAgain.click();
  await expect.poll(() => previewExists).toBe(false);
  await page.screenshot({ path: testInfo.outputPath("missing-search-incomplete-banner.png"), fullPage: true });

  await expect(page.getByText("Program nie zdążył ułożyć grafiku w dostępnym czasie. Możesz ponowić wyszukiwanie.")).toBeVisible();
  await expect(page.locator('[data-diag-action="replan-retry-incomplete"]')).toBeVisible();
});
