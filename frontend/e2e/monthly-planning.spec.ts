// ROTA-T031 (tasks/ROTA-T031/brief.md section 6, T31-10): E2E coverage
// for Planowanie miesiąca. Backend contract (compute, validation, exact
// deviation-set finalize) is covered by tests/test_t031_schedule_api.py --
// this file exercises the PLAN -> select -> reload -> finalize -> REPLAN
// UI loop against the real dev build + real backend. A freshly created
// site has an empty shift catalog/roster, so the solver's own job is
// trivial (zero demands/candidate assignments) -- that is enough to prove
// the screen's mechanics without duplicating rota/'s own solver test
// suite.
import { test, expect } from "@playwright/test";
import { createSite, openSite } from "./helpers";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

async function openMonthlyPlanning(page: import("@playwright/test").Page) {
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
  await expect(page.getByRole("heading", { name: "Planowanie miesiąca" })).toBeVisible();
}

// assemble_planning_state (rota/application/assembler.py) requires a
// CalendarDay row for every date in the target month -- PLAN cannot run
// without it. The existing Kalendarz modal (Workspace.tsx, out of T031's
// own scope) is the only current way to seed one; its "Wygeneruj
// kalendarz" button fills the whole real-world current month, which is
// also this screen's default selected month.
async function generateCalendarForCurrentMonth(page: import("@playwright/test").Page) {
  await page.locator('button[title="Kalendarz (dni robocze i święta)"]').click();
  await page.getByRole("button", { name: /Wygeneruj kalendarz na miesiąc/ }).click();
  await page.locator(".calendar-day-unconfigured").first().waitFor({ state: "detached" }).catch(() => undefined);
  await page.getByRole("button", { name: "Zamknij" }).click();
}

test("PLAN -> select candidate -> reload shows persisted version", async ({ page }) => {
  const siteName = `PLAN-SITE-${uid()}`;
  await createSite(page, siteName, `PLAN-PROF-${uid()}`);
  await generateCalendarForCurrentMonth(page);
  await openSite(page, siteName);
  await openMonthlyPlanning(page);

  await expect(page.getByText("Brak grafiku na ten miesiąc.")).toBeVisible();
  await page.locator('[data-diag-action="plan-month-first"]').click();

  await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
  await page.locator('[data-diag-action="select-candidate"]').first().click();

  await expect(page.getByText(/status: WORKING/)).toBeVisible();
  const versionText = await page.getByText(/Wersja: SV-/).textContent();
  const versionId = versionText?.match(/SV-[a-f0-9]+/)?.[0];
  expect(versionId).toBeTruthy();

  await page.reload();
  await openSite(page, siteName);
  await openMonthlyPlanning(page);
  await expect(page.getByText(new RegExp(`Wersja: ${versionId}`))).toBeVisible();
});

test("finalize with no deviations moves to FINAL, then REPLAN creates a new version", async ({ page }) => {
  const siteName = `PLAN-FIN-${uid()}`;
  await createSite(page, siteName, `PLAN-FIN-PROF-${uid()}`);
  await openSite(page, siteName);
  await openMonthlyPlanning(page);

  await page.locator('[data-diag-action="plan-month-first"]').click();
  await page.locator('[data-diag-action="select-candidate"]').first().click();
  await expect(page.getByText(/status: WORKING/)).toBeVisible();

  const parentVersionText = await page.getByText(/Wersja: SV-/).textContent();
  const parentVersionId = parentVersionText?.match(/SV-[a-f0-9]+/)?.[0];

  await page.locator('[data-diag-action="finalize-month"]').click();
  await expect(page.getByText(/status: FINAL_NO_DEVIATIONS/)).toBeVisible();

  await page.locator('[data-diag-action="replan-open"]').click();
  await page.locator('[data-diag-action="replan-submit"]').click();

  await expect(page.getByText(/status: WORKING/)).toBeVisible();
  const childVersionText = await page.getByText(/Wersja: SV-/).textContent();
  const childVersionId = childVersionText?.match(/SV-[a-f0-9]+/)?.[0];
  expect(childVersionId).not.toBe(parentVersionId);

  await page.locator('[data-diag-action="history-toggle"]').click();
  await expect(page.locator('[data-diag-action="restore-version"]')).toBeVisible();
});

// R1-1 (round-1 audit): month choice is limited to prev/current/next, and
// the PLAN-first effective_from date must resync when the selected month
// changes, not silently keep a stale month's date.
test("R1-1: exactly three selectable months, changing month resyncs the PLAN date", async ({ page }) => {
  const siteName = `PLAN-MONTHS-${uid()}`;
  await createSite(page, siteName, `PLAN-MONTHS-PROF-${uid()}`);
  await openSite(page, siteName);
  await openMonthlyPlanning(page);

  const monthSelect = page.getByLabel("Miesiąc");
  await expect(monthSelect.locator("option")).toHaveCount(3);

  const dateInput = page.locator('input[type="date"]');
  const initialValue = await dateInput.inputValue();

  await monthSelect.selectOption({ index: 0 });
  const newValue = await dateInput.inputValue();
  expect(newValue).not.toBe(initialValue);
});

// R1-2 (round-1 audit): DECISION_REQUIRED must be a persistent hard stop
// (backed by the existing current_decision_required readback), not a
// transient in-memory PlanningResult that vanishes on reload while the
// Finalizuj button stays visible. Real repro: a shift catalog row that
// needs a primary employee, zero roster.
test("R1-2: DECISION_REQUIRED is a persistent hard stop that survives reload", async ({ page }) => {
  const siteName = `PLAN-DECREQ-${uid()}`;
  await createSite(page, siteName, `PLAN-DECREQ-PROF-${uid()}`);
  await generateCalendarForCurrentMonth(page);
  await openSite(page, siteName);

  // Obiekt tab seeds one default row (D, 06:00-18:00, 1 required primary)
  // when the catalog is empty -- saving it with zero roster guarantees
  // DECISION_REQUIRED on PLAN.
  await page.locator('[data-diag-action="control-panel-tab-obiekt"]').click();
  await page.locator('[data-diag-action="shift-catalog-save"]').click();
  await expect(page.getByText("Zapisano.")).toBeVisible();

  await openMonthlyPlanning(page);
  await page.locator('[data-diag-action="plan-month-first"]').click();

  await expect(page.getByText(/Wymagana decyzja koordynatora/)).toBeVisible();
  await expect(page.locator('[data-diag-action="finalize-month"]')).toHaveCount(0);

  await page.reload();
  await openSite(page, siteName);
  await openMonthlyPlanning(page);
  await expect(page.getByText(/Wymagana decyzja koordynatora/)).toBeVisible();
  await expect(page.locator('[data-diag-action="finalize-month"]')).toHaveCount(0);
});

// R1-3 (round-1 audit): a rejected finalize (stale acknowledged set) must
// re-fetch the month view instead of leaving the coordinator stuck on the
// old deviation list with no way to re-confirm correctly.
test("R1-3: a rejected finalize re-fetches the month view", async ({ page }) => {
  const siteName = `PLAN-FINREFRESH-${uid()}`;
  await createSite(page, siteName, `PLAN-FINREFRESH-PROF-${uid()}`);
  await openSite(page, siteName);
  await openMonthlyPlanning(page);

  await page.locator('[data-diag-action="plan-month-first"]').click();
  await page.locator('[data-diag-action="select-candidate"]').first().click();
  await expect(page.getByText(/status: WORKING/)).toBeVisible();

  await page.route("**/schedule/*/finalize", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ status: 400, contentType: "application/json", body: JSON.stringify({ detail: "stale deviation set" }) });
    } else {
      await route.continue();
    }
  });

  const refreshedGet = page.waitForResponse(
    (r) => /\/schedule\/\d{4}-\d{2}-\d{2}$/.test(r.url()) && r.request().method() === "GET",
  );
  await page.locator('[data-diag-action="finalize-month"]').click();
  await expect(page.getByText("stale deviation set")).toBeVisible();
  await refreshedGet;
});
