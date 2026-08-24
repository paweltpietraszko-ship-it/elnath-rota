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
