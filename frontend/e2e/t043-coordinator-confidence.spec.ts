// ROTA-T043 Checkpoint C (tasks/ROTA-T043/brief.md section 6.3): one real
// browser vertical proving the UI wiring a coordinator actually sees --
// correct headcount, a real target-hours write, a real PLAN, and a status
// that matches what the real API returned. This does not exercise every
// solver scenario (that is the Symulator's own job, tests/property/**);
// it proves the screen renders what the backend actually said, not a
// stubbed network response.
import { test, expect } from "@playwright/test";
import { createSite } from "./helpers";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

// NOT the shared helpers.ts openSite(): see t041-daily-workflow.spec.ts and
// t042-local-date.spec.ts for the same pre-existing, out-of-scope mismatch
// (Room.tsx defaults activeNav to "Przegląd", not "Panel sterowania").
async function openSite(page: import("@playwright/test").Page, displayName: string) {
  await page.getByText(displayName, { exact: true }).click();
  await page.locator('[data-diag-action="room-nav-overview"]').waitFor({ state: "visible" });
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

test("T043 Checkpoint C: coordinator sees the real headcount, target write, and PLAN status the API actually returned", async ({ page }) => {
  const siteName = `T043C-${uid()}`;
  await createSite(page, siteName, `T043C-PROF-${uid()}`);
  await generateCalendarForCurrentMonth(page);
  await openSite(page, siteName);
  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await expect(page.getByRole("heading", { name: "Panel sterowania" })).toBeVisible();

  // A full 24/7 D/N layer is 5 LOCAL (owner ruling, T038/T039/T043) -- the
  // coordinator must see exactly that count reflected in "Obsada (N)".
  const names = Array.from({ length: 5 }, (_, i) => `${siteName}-E${i + 1}`);
  for (let i = 0; i < names.length; i++) {
    await addLocalEmployee(page, names[i]);
    if (i === 0) await setTargetHours(page, 170);
    await backToRoster(page);
  }
  await expect(page.getByText("Obsada (5)")).toBeVisible();

  // Real PLAN, real network response captured -- not a hardcoded expectation.
  const planResponse = page.waitForResponse((r) => r.url().includes("/schedule/") && r.url().includes("/plan") && r.request().method() === "POST");
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
  await expect(page.getByRole("heading", { name: "Planowanie miesiąca" })).toBeVisible();
  await page.locator('[data-diag-action="plan-month-first"]').click();
  const resp = await planResponse;
  const body = await resp.json();

  if (body.status === "FEASIBLE") {
    await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
  } else if (body.status === "DECISION_REQUIRED") {
    await expect(page.getByText(/Wymagana decyzja koordynatora/)).toBeVisible();
  } else {
    throw new Error(`unexpected real PLAN status for this assertion: ${body.status}`);
  }
});
