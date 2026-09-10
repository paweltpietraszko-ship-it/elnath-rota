// ROTA-T062 (brief section 9 Test scope; R1 finding 1, R5 finding R5-01, R6
// finding R6-01): the two mocked t062-*.spec.ts files prove the frontend
// renders a given API shape correctly, but neither exercises the real
// vertical the brief's own Test scope calls for -- "PLAN blocked -> czytelne
// działania -> rzeczywiste przejście do Obsady -> zmiana danych -> stara
// diagnoza znika -> ponowny PLAN". This is that test: a real backend, a real
// DECISION_REQUIRED, a real click-through to Obsada, a real data change, and
// a real re-plan proving the stale readback doesn't survive it
// (T62-02/03/04/08/14).
//
// The scenario reliably reaches a real LOAD-driven DECISION_REQUIRED: a full
// 24/7 D/N layer (owner ruling, T038/T039/T043: 5 LOCAL employees is the
// realistic baseline) with one employee blocked the whole month breaches the
// remaining four's weekly rolling-hours threshold. Two rounds of audit
// findings on the LOAD guidance text itself: R5-01 found the original text
// named an action ("accept the overtime") the product has no feature for;
// the R5 fix ("check staffing/availability for the overworked employee")
// still only described looking, not a change, and the test then performed a
// DIFFERENT, unannounced fix (ending an absence) than the employee it named
// (R6-01). OWNER_CORRECTED 2026-09-10: the coordinator picks who to add
// themselves -- T062 neither names a candidate nor judges that choice -- so
// decision_guidance.py's LOAD option now names the change directly, with no
// employee to get wrong: "Dodaj pracownika do obsady i zaplanuj ponownie".
// This test performs exactly that: adds a new employee (not the same type
// of fix as an earlier round, but now the ONLY type of fix the message
// names, so there is nothing left for the test to silently substitute).
import { expect, test } from "@playwright/test";
import { createSite, openSite } from "./helpers";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

async function generateCalendarForCurrentMonth(page: import("@playwright/test").Page) {
  await page.locator('button[title="Kalendarz (dni robocze i święta)"]').click();
  await page.getByRole("button", { name: /Wygeneruj kalendarz na miesiąc/ }).click();
  await page.locator(".calendar-day-unconfigured").first().waitFor({ state: "detached" }).catch(() => undefined);
  await page.getByRole("button", { name: "Zamknij" }).click();
}

async function addLocalEmployee(page: import("@playwright/test").Page, name: string) {
  await page.locator('[data-diag-action="roster-add-open"]').click();
  await page.locator('input[placeholder="np. Jan Kowalski"]').fill(name);
  await page.locator('[data-diag-action="add-person-submit"]').click();
  await expect(page.getByRole("heading", { name: "Godziny docelowe" })).toBeVisible();
}

async function setTargetHours(page: import("@playwright/test").Page, hours: number) {
  const row = page.locator(".field-row", { hasText: "Godziny docelowe" });
  await row.locator('input[type="number"]').fill(String(hours));
  await row.getByRole("button", { name: "Zapisz" }).click();
}

async function backToRoster(page: import("@playwright/test").Page) {
  await page.getByRole("button", { name: /Wróć do obsady/ }).click();
  await expect(page.getByRole("heading", { name: "Panel sterowania" })).toBeVisible();
}

function monthBounds(): { from: string; to: string } {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth(), 1);
  const to = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  return { from: iso(from), to: iso(to) };
}

test("T062 real vertical: blocked PLAN -> real guidance -> real Obsada change -> stale diagnosis clears -> replan FEASIBLE", async ({ page }) => {
  const siteName = `T062RV-${uid()}`;
  const blockedName = `${siteName}-Blocked`;
  await createSite(page, siteName);
  await generateCalendarForCurrentMonth(page);
  await openSite(page, siteName);

  // A freshly created site has NO shift demands at all until the Obiekt
  // tab's catalog is saved (monthly-planning.spec.ts R1-2's own proven
  // repro) -- without this, PLAN is trivially FEASIBLE (nothing to staff).
  // Full 24/7 D/N Standardowy layer (owner ruling, T038/T039/T043: 5 LOCAL
  // employees is the realistic baseline for this shape).
  await page.locator('[data-diag-action="control-panel-tab-obiekt"]').click();
  // Scoped to the "Katalog zmian" panel itself: the roster's own "Dodaj
  // osobę" form (elsewhere in the DOM, possibly kept mounted off-tab)
  // reuses the same generic ".create-panel" row class, so an unscoped
  // ".create-panel".last() can silently resolve to the wrong element.
  const catalogPanel = page.locator(".panel").filter({ hasText: "Katalog zmian" });
  await catalogPanel.locator('[data-diag-action="shift-catalog-add-row"]').click();
  const nightRow = catalogPanel.locator(".create-panel").last();
  await nightRow.locator("select").first().selectOption("N");
  await nightRow.locator('label:has-text("Początek") select').selectOption("18:00");
  await nightRow.locator('label:has-text("Koniec") select').selectOption("06:00");
  await catalogPanel.locator('[data-diag-action="shift-catalog-save"]').click();
  await expect(page.getByText("Zapisano.")).toBeVisible();
  await page.locator('[data-diag-action="control-panel-tab-obsada"]').click();

  // 5 LOCAL employees for the full 24/7 D/N layer; block one of the five
  // for the whole month via a real "Zgłoś nieobecność". Explicit
  // target_hours (matching t043-coordinator-confidence.spec.ts's own 170)
  // avoids the "brak wpisanego limitu -- równy podział" fallback warning
  // so the resulting decision is driven only by the real staffing gap.
  await addLocalEmployee(page, blockedName);
  await setTargetHours(page, 170);
  await backToRoster(page);
  for (let i = 2; i <= 5; i++) {
    await addLocalEmployee(page, `${siteName}-E${i}`);
    await setTargetHours(page, 170);
    await backToRoster(page);
  }

  // Block the first employee for the whole month via a real "Zgłoś
  // nieobecność" (Ogólna niedostępność / UNAVAILABLE_24H is the form's own
  // default selection).
  await page.getByRole("button", { name: blockedName, exact: true }).click();
  await page.getByRole("button", { name: "+ Zgłoś nieobecność" }).click();
  const { from, to } = monthBounds();
  // ROTA-T064: AddAbsenceForm now uses a real @daypicker/react range picker
  // (defaulting to workingMonth) instead of two raw <input type="date">
  // fields -- day buttons carry a "data-day" attribute with the exact ISO
  // date (see frontend/e2e/t064-calendar-dates.spec.ts for the same
  // pattern). This was a dead selector after a legal T064 control swap,
  // not a product regression (Codex R3, main@dc9f979).
  await page.locator(`[data-day="${from}"]`).click();
  await page.locator(`[data-day="${to}"]`).click();
  await page.getByRole("button", { name: "Zgłoś", exact: true }).click();
  await expect(page.getByText(`Ogólna niedostępność — od ${from} do ${to}`)).toBeVisible();
  await backToRoster(page);

  // Real PLAN, real network response: removing 1 of the 5-employee 24/7
  // D/N layer for the whole month breaches the weekly rolling-hours
  // threshold for the remaining 4 -- a real LOAD-driven DECISION_REQUIRED.
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
  await expect(page.getByRole("heading", { name: "Planowanie miesiąca" })).toBeVisible();
  const firstPlan = page.waitForResponse((r) => r.url().includes("/schedule/") && r.url().includes("/plan") && r.request().method() === "POST");
  await page.locator('[data-diag-action="plan-month-first"]').click();
  const firstBody = await (await firstPlan).json();
  expect(firstBody.status).toBe("DECISION_REQUIRED");
  await expect(page.getByText(/Wymagana decyzja koordynatora/)).toBeVisible();
  // T62-03: no raw technical word leaks into this screen's own banner.
  await expect(page.getByText("solver", { exact: false })).toHaveCount(0);
  // T62-02: concrete, evidence-backed action text shown here directly -- a
  // real change ("add"), not just an observation ("check") (R6-01). No
  // employee name to get wrong (OWNER_CORRECTED: coordinator's own choice).
  const loadOptionText = "Dodaj pracownika do obsady i zaplanuj ponownie";
  await expect(page.getByText(loadOptionText)).toBeVisible();

  // Real click-through to Decyzje koordynatora -> real navigation to Obsada
  // (T62-04): the LOAD option carries target="obsada", a real, existing
  // place -- click exactly the action shown.
  await page.locator('[data-diag-action="room-nav-decisions"]').click();
  const actionButton = page.getByRole("button", { name: loadOptionText });
  await expect(actionButton).toBeVisible();
  await actionButton.click();
  await expect(page.getByRole("heading", { name: "Lista pracowników" })).toBeVisible();

  // Real data change on Obsada: perform EXACTLY the shown action -- add a
  // new employee to staffing (R6-01: the vertical must not substitute a
  // different, unannounced fix for the one displayed). "Lista pracowników"
  // is the roster section of this same Panel sterowania/Obsada screen, not
  // a separate page -- addLocalEmployee can be called directly here.
  await addLocalEmployee(page, `${siteName}-E6`);
  await setTargetHours(page, 170);
  await backToRoster(page);

  // T62-08: the stale DECISION_REQUIRED must not survive the real data
  // change that made it moot (durable_inputs.py's update_membership
  // invalidates the persisted readback for any new roster membership) --
  // the banner must already be gone here, BEFORE any new PLAN runs, and a
  // fresh PLAN must be both required and reach FEASIBLE (6 employees now
  // cover the 5-person baseline, T038/T039/T043, plus the still-blocked one).
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
  await expect(page.getByRole("heading", { name: "Planowanie miesiąca" })).toBeVisible();
  await expect(page.getByText(/Wymagana decyzja koordynatora/)).toHaveCount(0);
  await expect(page.locator('[data-diag-action="plan-month-first"]')).toBeVisible();
  const secondPlan = page.waitForResponse((r) => r.url().includes("/schedule/") && r.url().includes("/plan") && r.request().method() === "POST");
  await page.locator('[data-diag-action="plan-month-first"]').click();
  const secondBody = await (await secondPlan).json();
  expect(secondBody.status).toBe("FEASIBLE");
  await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
  await expect(page.getByText(/Wymagana decyzja koordynatora/)).toHaveCount(0);
});
