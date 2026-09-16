// ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID (brief.md
// TASK_SCOPE): end-to-end coverage that a LOCAL employee whose only
// activity this month is an active DELEGACJA -- zero Assignments -- still
// shows up on the "Planowanie miesiąca" grid, with a DEL cell on every day
// the record covers, both in the immediate PLAN result and in the
// persisted, unaccepted PlanPreview after a reload (DG-01/02/03/04/08).
import { test, expect } from "@playwright/test";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

// Mirrors frontend/e2e/target-hours-required.spec.ts's own OCHRONA helper --
// helpers.ts's createSite is ORDINARY and needs a role catalog first, which
// is unrelated to what this file tests.
async function createOchronaSite(page: import("@playwright/test").Page, displayName: string) {
  await page.goto("/");
  await page.locator('[data-diag-action="create-site-open"]').click();
  await page.locator('input[placeholder="np. NORDPLAST II"]').fill(displayName);
  await page.locator('[data-diag-action="create-site-submit"]').click();
  await page.getByText(displayName, { exact: true }).waitFor();
}

async function generateCalendarForCurrentMonth(page: import("@playwright/test").Page) {
  await page.locator('button[title="Kalendarz (dni robocze i święta)"]').click();
  await page.getByRole("button", { name: /Wygeneruj kalendarz na miesiąc/ }).click();
  await page.locator(".calendar-day-unconfigured").first().waitFor({ state: "detached" }).catch(() => undefined);
  await page.getByRole("button", { name: "Zamknij" }).click();
}

async function openSite(page: import("@playwright/test").Page, displayName: string) {
  await page.getByText(displayName, { exact: true }).click();
  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await page.getByRole("heading", { name: "Panel sterowania" }).waitFor();
}

// The DELEGACJA form refuses to submit until the Site has a default hours
// value (EmployeeAvailability.tsx AddAbsenceForm) -- set once per site.
async function setSiteDelegationDefaultHours(page: import("@playwright/test").Page, hours: number) {
  await page.locator('[data-diag-action="control-panel-tab-obiekt"]').click();
  const panel = page.locator(".panel", { has: page.getByRole("heading", { name: "Domyślne godziny delegacji" }) });
  const input = panel.getByLabel("Godziny dziennie");
  await input.waitFor();
  await input.fill(String(hours));
  await expect(input).toHaveValue(String(hours));
  await panel.getByRole("button", { name: "Zapisz" }).click();
  await expect(panel.getByText("Zapisano.")).toBeVisible();
  await page.locator('[data-diag-action="control-panel-tab-obsada"]').click();
}

async function addLocalEmployee(page: import("@playwright/test").Page, displayName: string) {
  await page.locator('[data-diag-action="roster-add-open"]').click();
  await page.locator('input[placeholder="np. Jan Kowalski"]').fill(displayName);
  await page.locator('[data-diag-action="add-person-submit"]').click();
  await expect(page.getByRole("heading", { name: displayName })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Godziny docelowe" })).toBeVisible();
}

async function setTargetHours(page: import("@playwright/test").Page, hours: number) {
  await page.locator('input[type="number"]').last().fill(String(hours));
  await page.getByRole("button", { name: "Zapisz" }).click();
  // Same "ustawić wszystkim?" prompt frontend/e2e/target-hours-required.spec.ts
  // already documents -- declined here so it never touches other employees.
  const prompt = page.locator('[data-diag-action="target-hours-apply-all-prompt"]');
  await prompt.waitFor();
  await prompt.getByRole("button", { name: "Nie", exact: true }).click();
}

function currentMonthRange(): { firstIso: string; lastIso: string; daysInMonth: number } {
  const now = new Date();
  const first = new Date(now.getFullYear(), now.getMonth(), 1);
  const last = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const toIso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  return { firstIso: toIso(first), lastIso: toIso(last), daysInMonth: last.getDate() };
}

// Whole-month DELEGACJA -- the exact "DEL-only, zero Assignments" shape the
// brief's owner decision targets. dailyHours is chosen by the caller to make
// this employee's effective (remaining) target exactly 0, so the solver has
// no reason to ever assign them real work.
async function reportFullMonthDelegation(page: import("@playwright/test").Page, dailyHours: number): Promise<void> {
  const { firstIso, lastIso } = currentMonthRange();
  await page.getByRole("button", { name: "+ Zgłoś nieobecność" }).click();
  await page.locator('label:has-text("Powód") select').selectOption("DELEGACJA");
  await page.locator(`[data-day="${firstIso}"]`).click();
  await page.locator(`[data-day="${lastIso}"]`).click();
  await page.getByLabel("Godziny delegacji (dziennie)").fill(String(dailyHours));
  await page.getByRole("button", { name: "Zgłoś", exact: true }).click();
  await expect(page.getByText(`Delegacja — od ${firstIso} do ${lastIso}`)).toBeVisible();
}

async function backToRoster(page: import("@playwright/test").Page) {
  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await expect(page.getByRole("heading", { name: "Panel sterowania" })).toBeVisible();
}

async function openMonthlyPlanning(page: import("@playwright/test").Page) {
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
  await expect(page.getByRole("heading", { name: "Planowanie miesiąca" })).toBeVisible();
}

const DAILY_DELEGATION_HOURS = 8;

test("DEL-only employee appears in PLAN preview and survives reload without accepting", async ({ page }) => {
  const siteName = `DG-SITE-${uid()}`;
  await createOchronaSite(page, siteName);
  await generateCalendarForCurrentMonth(page);
  await openSite(page, siteName);
  await setSiteDelegationDefaultHours(page, DAILY_DELEGATION_HOURS);

  // Two real workers, same proven fixture pattern as
  // frontend/e2e/target-hours-required.spec.ts -- cover the month's actual
  // demand between them.
  await addLocalEmployee(page, "Anna Testowa");
  await setTargetHours(page, 100);
  await backToRoster(page);
  await addLocalEmployee(page, "Bartek Testowy");
  await setTargetHours(page, 100);
  await backToRoster(page);

  // Third employee: full-month DELEGACJA, target set exactly to her month's
  // delegation hours so her remaining target is 0 -- the solver has nothing
  // left to assign her.
  await addLocalEmployee(page, "Celina Delegowana");
  await reportFullMonthDelegation(page, DAILY_DELEGATION_HOURS);
  const { daysInMonth } = currentMonthRange();
  await setTargetHours(page, DAILY_DELEGATION_HOURS * daysInMonth);
  await backToRoster(page);

  await openMonthlyPlanning(page);
  await page.locator('[data-diag-action="plan-month-first"]').click();
  await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();

  const candidateRow = page.getByRole("row", { name: /Celina Delegowana/ });
  await expect(candidateRow).toBeVisible();
  // DG-03/DG-04: one DEL per covered day, hours summed into the row total.
  expect(await candidateRow.getByText("DEL", { exact: true }).count()).toBe(daysInMonth);
  await expect(candidateRow).toContainText(`${DAILY_DELEGATION_HOURS * daysInMonth}h`);

  // DG-02: reload -- no candidate was accepted, so this reconstructs from
  // the persisted, unaccepted PlanPreview, not a fresh solver run.
  await page.reload();
  await openSite(page, siteName);
  await openMonthlyPlanning(page);
  await expect(page.getByText("Niezatwierdzony wynik PLAN")).toBeVisible();
  const previewRow = page.getByRole("row", { name: /Celina Delegowana/ });
  await expect(previewRow).toBeVisible();
  expect(await previewRow.getByText("DEL", { exact: true }).count()).toBe(daysInMonth);
  await expect(previewRow).toContainText(`${DAILY_DELEGATION_HOURS * daysInMonth}h`);
});

test("DEL-only employee keeps her DEL row and total hours after the candidate is accepted", async ({ page }) => {
  const siteName = `DG-ACCEPT-${uid()}`;
  await createOchronaSite(page, siteName);
  await generateCalendarForCurrentMonth(page);
  await openSite(page, siteName);
  await setSiteDelegationDefaultHours(page, DAILY_DELEGATION_HOURS);

  await addLocalEmployee(page, "Anna Testowa");
  await setTargetHours(page, 100);
  await backToRoster(page);
  await addLocalEmployee(page, "Bartek Testowy");
  await setTargetHours(page, 100);
  await backToRoster(page);

  await addLocalEmployee(page, "Celina Delegowana");
  await reportFullMonthDelegation(page, DAILY_DELEGATION_HOURS);
  const { daysInMonth } = currentMonthRange();
  await setTargetHours(page, DAILY_DELEGATION_HOURS * daysInMonth);
  await backToRoster(page);

  await openMonthlyPlanning(page);
  await page.locator('[data-diag-action="plan-month-first"]').click();
  await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
  await page.locator('[data-diag-action="select-candidate"]').first().click();
  await expect(page.getByText(/Status: Wersja robocza,/)).toBeVisible();

  const row = page.getByRole("row", { name: /Celina Delegowana/ });
  await expect(row).toBeVisible();
  expect(await row.getByText("DEL", { exact: true }).count()).toBe(daysInMonth);
  await expect(row).toContainText(`${DAILY_DELEGATION_HOURS * daysInMonth}h`);

  // Regression: employees with no DELEGACJA are unaffected by this Task's
  // roster/DEL projection -- their rows never pick up a stray DEL cell.
  // (This quick-created site's shift catalog is an unsaved draft -- no real
  // demand exists, so Anna/Bartek's own Assignment-driven totals are
  // legitimately 0h here; the "real Assignments + no DELEGACJA" regression
  // is covered with an actual solved schedule in
  // tests/test_delegation_schedule_grid.py at the backend/API level.)
  const annaRow = page.getByRole("row", { name: /Anna Testowa/ });
  const bartekRow = page.getByRole("row", { name: /Bartek Testowy/ });
  await expect(annaRow).toBeVisible();
  await expect(bartekRow).toBeVisible();
  expect(await annaRow.getByText("DEL", { exact: true }).count()).toBe(0);
  expect(await bartekRow.getByText("DEL", { exact: true }).count()).toBe(0);
});
