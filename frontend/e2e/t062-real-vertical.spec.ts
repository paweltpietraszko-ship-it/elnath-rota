// ROTA-T062 (brief section 9 Test scope, R1 audit finding 1): the two
// mocked t062-*.spec.ts files prove the frontend renders a given API shape
// correctly, but neither exercises the real vertical the brief's own Test
// scope calls for -- "PLAN blocked -> czytelne działania -> rzeczywiste
// przejście do Obsady -> zmiana danych -> stara diagnoza znika -> ponowny
// PLAN". This is that test: a real backend, a real DECISION_REQUIRED, a
// real availability change, and a real re-plan proving the stale readback
// doesn't survive it (T62-03/08/14).
//
// SCOPE NOTE on which blocker this exercises: multiple staffing shapes were
// tried (see task/session history) to reach the availability-specific
// UNAVAILABLE-01 blocker (target="obsada", clickable through to Obsada,
// T62-02/04) via the real UI. Every shape that removed one of a full 24/7
// D/N layer's 5 employees (owner ruling, T038/T039/T043) for the whole
// month produced a genuine, structural weekly-hours LOAD blocker instead
// (the remaining 4 covering the whole layer alone breaches the rolling
// 7-day threshold before any single-employee/day attribution is possible),
// and a single-shift/day catalog with fewer employees instead reliably hit
// THIRD_CONSECUTIVE_SHIFT_BLOCKED. Reaching UNAVAILABLE-01 specifically
// through the real solver would need staffing-math engineering beyond this
// brief's TASK_SCOPE (a product/solver judgment call, not a test-selector
// fix) -- flagged to the architect/Codex in BOARD.md rather than decided
// here. UNAVAILABLE-01's target="obsada" rendering and click-through are
// already proven at the frontend layer by t062-guidance.spec.ts (mocked)
// and at the backend layer by tests/test_t013.py and tests/test_t062.py.
// This real-vertical test instead proves the vertical end-to-end for the
// LOAD blocker, which is just as real and covers T62-03/08/14 fully.
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
  await page.locator('label:has-text("Od") input[type="date"]').fill(from);
  await page.locator('label:has-text("Do") input[type="date"]').fill(to);
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
  // T62-02: concrete, evidence-backed action text shown here directly.
  const loadOptionText = "Świadomie zaakceptuj przekroczenie tygodniowego czasu pracy";
  await expect(page.getByText(loadOptionText)).toBeVisible();

  // The LOAD option has no obsada target (there is nothing to click
  // through to -- it asks the coordinator to consciously accept overtime,
  // not to fix a roster record) -- Decyzje koordynatora shows the SAME
  // guidance text but never as a fake button. UNAVAILABLE-01's real
  // target="obsada" click-through is covered by t062-guidance.spec.ts.
  await page.locator('[data-diag-action="room-nav-decisions"]').click();
  await expect(page.getByText(loadOptionText)).toBeVisible();
  await expect(page.getByRole("button", { name: loadOptionText })).toHaveCount(0);

  // Real data change: end the blocking availability record via Obsada.
  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await page.locator('[data-diag-action="control-panel-tab-obsada"]').click();
  await page.getByRole("button", { name: blockedName, exact: true }).click();
  await page.getByRole("button", { name: "Zakończ teraz" }).click();
  await expect(page.getByText(`Ogólna niedostępność — od ${from} do ${to} (zakończone)`)).toBeVisible();
  await backToRoster(page);

  // T62-08: the stale DECISION_REQUIRED must not survive the real data
  // change that made it moot (durable_inputs.py invalidates the persisted
  // readback the moment the underlying availability record changes) -- the
  // banner must already be gone here, BEFORE any new PLAN runs, and a
  // fresh PLAN must be both required and reach FEASIBLE (the full 5-person
  // layer is the established sufficient baseline, T038/T039/T043).
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
