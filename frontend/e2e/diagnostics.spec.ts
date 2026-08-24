// ROTA-T021c section 5: acceptance matrix. Every scenario drives the
// real Vite dev build against the real FastAPI backend (playwright.config.ts
// webServer) -- no source-level tests, no direct function calls.
import { test, expect } from "@playwright/test";
import {
  createSite,
  openSite,
  downloadFrontendReport,
  downloadDiagnosticZip,
  waitForWorkspaceLoaded,
} from "./helpers";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

test("1: render crash never shows a white screen, gives a code, and a local export", async ({ page }) => {
  await page.goto("/");
  await page.locator('[data-diag-action="diag-test-render-crash"]').click();

  await expect(page.getByText("Coś poszło nie tak")).toBeVisible();
  const codeText = await page.locator("strong").first().textContent();
  expect(codeText).toMatch(/^[A-Z0-9]{6}$/);

  const report = await downloadFrontendReport(page);
  const events = report.events as Array<{ kind: string; diagnostic_code?: string }>;
  const renderError = events.find((e) => e.kind === "RENDER_ERROR");
  expect(renderError).toBeTruthy();
  expect(renderError?.diagnostic_code).toBe(codeText);
});

test("2: window.error and unhandledrejection each produce their own event", async ({ page }) => {
  await page.goto("/");
  await page.locator('[data-diag-action="diag-test-unhandled-error"]').click();
  await page.locator('[data-diag-action="diag-test-unhandled-rejection"]').click();
  await page.waitForTimeout(200);

  await createSite(page, `CHK-SITE-${uid()}`, `CHK-PROF-${uid()}`);
  const { frontendReport } = await downloadDiagnosticZip(page);
  const events = (frontendReport!.events as Array<{ kind: string }>).map((e) => e.kind);
  expect(events).toContain("UNHANDLED_ERROR");
  expect(events).toContain("UNHANDLED_REJECTION");
});

test("3: API 500 -- click, request start and request failed share one action_id", async ({ page }) => {
  await page.route("**/api/workspace/sites", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "boom" }) });
    } else {
      await route.continue();
    }
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Nowy obiekt (Standardowy)" }).click();
  await page.locator('input[placeholder="np. NORDPLAST II"]').fill(`FAIL-SITE-${uid()}`);
  await page.locator('input[placeholder="np. PROF-NORDPLAST-02"]').fill(`FAIL-PROF-${uid()}`);
  await page.locator('[data-diag-action="create-site-submit"]').click();
  await expect(page.getByText("boom")).toBeVisible();

  await page.unroute("**/api/workspace/sites");
  await createSite(page, `CHK2-SITE-${uid()}`, `CHK2-PROF-${uid()}`);
  const { frontendReport } = await downloadDiagnosticZip(page);
  const events = frontendReport!.events as Array<{ kind: string; action_id?: string | null }>;

  const failed = events.find((e) => e.kind === "REQUEST_FAILED");
  expect(failed).toBeTruthy();
  expect(failed!.action_id).toBeTruthy();
  const started = events.find((e) => e.kind === "REQUEST_STARTED" && e.action_id === failed!.action_id);
  const click = events.find((e) => e.kind === "CLICK_RECEIVED" && e.action_id === failed!.action_id);
  expect(started).toBeTruthy();
  expect(click).toBeTruthy();

  const stalledForThatAction = events.find((e) => e.kind === "ACTION_STALLED" && e.action_id === failed!.action_id);
  expect(stalledForThatAction).toBeFalsy();
});

test("4: a hung request produces REQUEST_TIMEOUT, not a false ACTION_STALLED", async ({ page }) => {
  test.slow();
  await page.route("**/api/workspace/sites", async (route) => {
    if (route.request().method() === "POST") {
      await new Promise(() => {
        /* never resolves -- request.abort()/fulfill() intentionally never called */
      });
    } else {
      await route.continue();
    }
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Nowy obiekt (Standardowy)" }).click();
  await page.locator('input[placeholder="np. NORDPLAST II"]').fill(`HANG-SITE-${uid()}`);
  await page.locator('input[placeholder="np. PROF-NORDPLAST-02"]').fill(`HANG-PROF-${uid()}`);
  await page.locator('[data-diag-action="create-site-submit"]').click();
  await expect(page.getByText("limit czasu")).toBeVisible({ timeout: 25000 });

  await page.unroute("**/api/workspace/sites");
  await createSite(page, `CHK3-SITE-${uid()}`, `CHK3-PROF-${uid()}`);
  const { frontendReport } = await downloadDiagnosticZip(page);
  const events = frontendReport!.events as Array<{ kind: string; action_id?: string | null }>;

  const timeout = events.find((e) => e.kind === "REQUEST_TIMEOUT");
  expect(timeout).toBeTruthy();
  const falseStall = events.find((e) => e.kind === "ACTION_STALLED" && e.action_id === timeout!.action_id);
  expect(falseStall).toBeFalsy();
});

test("5: a control with no handler/effect is reported ACTION_STALLED", async ({ page }) => {
  await page.goto("/");
  await waitForWorkspaceLoaded(page);
  await page.locator('[data-diag-action="diag-test-inert"]').click();
  await page.waitForTimeout(1200);

  await createSite(page, `CHK4-SITE-${uid()}`, `CHK4-PROF-${uid()}`);
  const { frontendReport } = await downloadDiagnosticZip(page);
  const events = frontendReport!.events as Array<{ kind: string; action: string }>;
  const stalled = events.find((e) => e.kind === "ACTION_STALLED" && e.action === "diag-test-inert");
  expect(stalled).toBeTruthy();
});

test("6: a valid local no-op and a valid API action never get flagged stalled", async ({ page }) => {
  await page.goto("/");
  await page.locator('[data-diag-action="diag-test-explicit-noop"]').click();
  await page.waitForTimeout(1200);

  const siteName = `CHK5-SITE-${uid()}`;
  await createSite(page, siteName, `CHK5-PROF-${uid()}`);
  await page.waitForTimeout(1200);

  const { frontendReport } = await downloadDiagnosticZip(page);
  const events = frontendReport!.events as Array<{ kind: string; action?: string }>;
  const noop = events.find((e) => e.kind === "ACTION_NOOP" && e.action === "diag-test-explicit-noop");
  expect(noop).toBeTruthy();
  const anyStalled = events.filter((e) => e.kind === "ACTION_STALLED");
  expect(anyStalled).toHaveLength(0);
});

test("7: events survive a reload after a crash", async ({ page }) => {
  await page.goto("/");
  await page.locator('[data-diag-action="diag-test-render-crash"]').click();
  await expect(page.getByText("Coś poszło nie tak")).toBeVisible();

  await page.reload();
  await createSite(page, `CHK6-SITE-${uid()}`, `CHK6-PROF-${uid()}`);
  const { frontendReport } = await downloadDiagnosticZip(page);
  const events = frontendReport!.events as Array<{ kind: string }>;
  expect(events.some((e) => e.kind === "RENDER_ERROR")).toBe(true);
});

test("8: the existing ZIP stays openable, keeps diagnostics.json, and gains the frontend report", async ({ page }) => {
  await page.goto("/");
  await createSite(page, `CHK7-SITE-${uid()}`, `CHK7-PROF-${uid()}`);
  const { raw, frontendReport } = await downloadDiagnosticZip(page);

  const AdmZip = (await import("adm-zip")).default;
  const zip = new AdmZip(raw);
  const names = zip.getEntries().map((e) => e.entryName);
  expect(names).toContain("diagnostics.json");
  expect(names).toContain("frontend_diagnostics.json");
  const diagnosticsJson = JSON.parse(zip.getEntry("diagnostics.json")!.getData().toString("utf-8"));
  expect(diagnosticsJson).toBeTruthy();
  expect(frontendReport).toBeTruthy();
});

test("9: with the API unreachable, the local frontend export still works", async ({ page }) => {
  await page.goto("/");
  await page.locator('[data-diag-action="diag-test-render-crash"]').click();
  await expect(page.getByText("Coś poszło nie tak")).toBeVisible();

  await page.route("**/api/**", (route) => route.abort());
  const report = await downloadFrontendReport(page);
  expect(report.schema_version).toBe(1);
  expect(Array.isArray(report.events)).toBe(true);
});

test("10: privacy canary -- names, form content, and failed-request bodies never leak into any export", async ({
  page,
}) => {
  const canarySite = `CANARY-SITE-${uid()}`;
  const canaryProfile = `CANARY-PROFILE-${uid()}`;
  const canaryEmployee = `CANARY-EMP-${uid()}`;
  const canaryBody = `CANARY-BODY-${uid()}`;

  // Deliberately stays on ControlPanel (roster) rather than opening
  // EmployeeDetail: that screen fires several concurrent GETs on mount,
  // which collides with the unrelated, already-flagged api/deps.py
  // thread-affinity race (see project_sqlite_thread_affinity_bug_found
  // memory) far too often for a deterministic privacy check. The
  // failing-request/canary-body path is exercised just as well via the
  // roster attach call.
  await page.route("**/api/workspace/sites/*/roster", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: canaryBody }) });
    } else {
      await route.continue();
    }
  });

  await createSite(page, canarySite, canaryProfile);
  await openSite(page, canarySite);
  await page.locator('[data-diag-action="roster-add-open"]').click();
  await page.locator('input[placeholder="np. Jan Kowalski"]').fill(canaryEmployee);
  await page.locator('[data-diag-action="add-person-submit"]').click();
  await page.locator(".create-panel .banner-error").waitFor({ timeout: 10000 });

  // "Pobierz pakiet diagnostyczny" lives on Workspace, not this screen.
  await page.locator('[data-diag-action="breadcrumb-back"]').click();
  await page.getByRole("heading", { name: "Twoje obiekty" }).waitFor();

  const { raw, frontendReport } = await downloadDiagnosticZip(page);
  const zipText = raw.toString("latin1"); // scan raw bytes too, not just the parsed JSON entry

  for (const canary of [canarySite, canaryProfile, canaryEmployee, canaryBody]) {
    expect(JSON.stringify(frontendReport)).not.toContain(canary);
    expect(zipText).not.toContain(canary);
  }
});
