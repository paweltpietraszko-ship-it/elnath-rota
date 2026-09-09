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
  await createSite(page, siteName);
  await generateCalendarForCurrentMonth(page);
  await openSite(page, siteName);
  await openMonthlyPlanning(page);

  await expect(page.getByText("Brak grafiku na ten miesiąc.")).toBeVisible();
  await page.locator('[data-diag-action="plan-month-first"]').click();

  await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
  await page.locator('[data-diag-action="select-candidate"]').first().click();

  // ROTA-T048 removed the raw version_id display entirely -- "Status: {label},
  // utworzono {timestamp}" (second-precision, see formatDateTime's own
  // comment) is what a coordinator actually sees now, and disambiguates
  // versions just as well as the old SV-... id did.
  await expect(page.getByText(/Status: Wersja robocza,/)).toBeVisible();
  const statusText = await page.getByText(/Status: .+, utworzono .+/).textContent();
  expect(statusText).toBeTruthy();

  await page.reload();
  await openSite(page, siteName);
  await openMonthlyPlanning(page);
  await expect(page.getByText(statusText!)).toBeVisible();
});

// SKIPPED (2026-09-09, found while fixing this file's stale "status: WORKING"
// text): this test's post-finalize step assumed a `replan-open` ->
// `replan-submit` two-step dialog, which no longer exists anywhere in
// MonthlyPlanning.tsx. Per that screen's own T057-follow-up comment
// (2026-09-07): "REPLAN's actual entry point ... only makes sense
// pre-acceptance; Przelicz Plan's own preview (post-acceptance, same
// 'Kandydaci' panel) never offers it." So a finalized month's "give me a
// new version" flow is now Przelicz Plan, going back through the ordinary
// PLAN-candidates panel -- a different UI flow than what this test
// exercises, not a renamed button. Same class of pre-existing T057 gap
// already flagged elsewhere this project (BOARD.md/ROTA-TEST-CLEANUP's
// test_t011_e Route A finding) -- flagging, not guessing at a rewrite.
test.skip("finalize with no deviations moves to FINAL, then REPLAN creates a new version", async ({ page }) => {
  const siteName = `PLAN-FIN-${uid()}`;
  await createSite(page, siteName);
  await openSite(page, siteName);
  await openMonthlyPlanning(page);

  await page.locator('[data-diag-action="plan-month-first"]').click();
  await page.locator('[data-diag-action="select-candidate"]').first().click();
  await expect(page.getByText(/Status: Wersja robocza,/)).toBeVisible();

  // ROTA-T048 removed the raw version_id display -- the status+timestamp
  // line (second-precision) is the current, correct way to tell two
  // versions apart on screen.
  const parentStatusText = await page.getByText(/Status: .+, utworzono .+/).textContent();

  await page.locator('[data-diag-action="finalize-month"]').click();
  await expect(page.getByText(/Status: Zatwierdzona,/)).toBeVisible();

  await page.locator('[data-diag-action="replan-open"]').click();
  await page.locator('[data-diag-action="replan-submit"]').click();

  await expect(page.getByText(/Status: Wersja robocza,/)).toBeVisible();
  const childStatusText = await page.getByText(/Status: .+, utworzono .+/).textContent();
  expect(childStatusText).not.toBe(parentStatusText);

  await page.locator('[data-diag-action="history-toggle"]').click();
  await expect(page.locator('[data-diag-action="restore-version"]')).toBeVisible();
});

// R1-1 (round-1 audit): the PLAN-first effective_from date must resync when
// the selected month changes, not silently keep a stale month's date.
// ROTA-T053: the month is no longer this screen's own <select> (limited to
// prev/current/next) -- it's the free Room-level "Miesiąc roboczy" input
// shared across screens.
test("R1-1: changing the working month resyncs the PLAN date", async ({ page }) => {
  const siteName = `PLAN-MONTHS-${uid()}`;
  await createSite(page, siteName);
  await openSite(page, siteName);
  await openMonthlyPlanning(page);

  const monthInput = page.locator('input[type="month"]');
  const dateInput = page.locator('input[type="date"]');
  const initialValue = await dateInput.inputValue();

  const [year, month] = (await monthInput.inputValue()).split("-").map(Number);
  const previous = new Date(year, month - 2, 1);
  await monthInput.fill(`${previous.getFullYear()}-${String(previous.getMonth() + 1).padStart(2, "0")}`);

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
  await createSite(page, siteName);
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
  await createSite(page, siteName);
  await openSite(page, siteName);
  await openMonthlyPlanning(page);

  await page.locator('[data-diag-action="plan-month-first"]').click();
  await page.locator('[data-diag-action="select-candidate"]').first().click();
  await expect(page.getByText(/Status: Wersja robocza,/)).toBeVisible();

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
