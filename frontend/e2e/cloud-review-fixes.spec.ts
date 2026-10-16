// ROTA-CLOUD-REVIEW-FIXES F6/O4 (A1): an L4 recorded after a schedule was
// accepted is shown on the real "Planowanie miesiąca" screen, in Polish,
// with the person and the day, and disappears once the L4 is withdrawn --
// not first at PDF export. Setup follows the proven OCHRONA pattern of
// frontend/e2e/delegation-schedule-grid.spec.ts; only the L4 write itself
// goes through the same HTTP endpoint the absence form uses.
import { test, expect, Page } from "@playwright/test";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

async function createOchronaSite(page: Page, displayName: string) {
  await page.goto("/");
  await page.locator('[data-diag-action="create-site-open"]').click();
  await page.locator('input[placeholder="np. NORDPLAST II"]').fill(displayName);
  await page.locator('[data-diag-action="create-site-submit"]').click();
  await page.getByText(displayName, { exact: true }).waitFor();
}

async function generateCalendarForCurrentMonth(page: Page) {
  await page.locator('button[title="Kalendarz (dni robocze i święta)"]').click();
  await page.getByRole("button", { name: /Wygeneruj kalendarz na miesiąc/ }).click();
  await page.locator(".calendar-day-unconfigured").first().waitFor({ state: "detached" }).catch(() => undefined);
  await page.getByRole("button", { name: "Zamknij" }).click();
}

async function openSite(page: Page, displayName: string) {
  await page.getByText(displayName, { exact: true }).click();
  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await page.getByRole("heading", { name: "Panel sterowania" }).waitFor();
}

async function addLocalEmployee(page: Page, displayName: string) {
  await page.locator('[data-diag-action="roster-add-open"]').click();
  await page.locator('input[placeholder="np. Jan Kowalski"]').fill(displayName);
  await page.locator('[data-diag-action="add-person-submit"]').click();
  await expect(page.getByRole("heading", { name: displayName })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Godziny docelowe" })).toBeVisible();
  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await expect(page.getByRole("heading", { name: "Panel sterowania" })).toBeVisible();
}

async function openMonthlyPlanning(page: Page) {
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
  await expect(page.getByRole("heading", { name: "Planowanie miesiąca" })).toBeVisible();
}

function iso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

test("L4 added after acceptance is shown in the month banner and disappears after it is withdrawn", async ({ page }) => {
  const now = new Date();
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  test.skip(now.getDate() >= lastDay, "needs at least one future day left in the current month");

  const siteName = `CR-F6-${uid()}`;
  await createOchronaSite(page, siteName);
  await generateCalendarForCurrentMonth(page);
  await openSite(page, siteName);
  const sites = await (await page.request.get("/api/workspace/sites")).json();
  const siteId: string = sites.find((s: { display_name: string }) => s.display_name === siteName).site_id;
  // Obiekt tab seeds one default row (D, 06:00-18:00, 1 required primary)
  // when the catalog is empty -- same step as frontend/e2e/monthly-planning.spec.ts.
  await page.locator('[data-diag-action="control-panel-tab-obiekt"]').click();
  await page.locator('[data-diag-action="shift-catalog-save"]').click();
  await expect(page.getByText("Zapisano.")).toBeVisible();
  await page.locator('[data-diag-action="control-panel-tab-obsada"]').click();
  await addLocalEmployee(page, "Anna Testowa");
  await addLocalEmployee(page, "Bartek Testowy");
  await addLocalEmployee(page, "Celina Testowa");

  await openMonthlyPlanning(page);
  await page.locator('[data-diag-action="plan-month-first"]').click();
  await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
  await page.locator('[data-diag-action="select-candidate"]').first().click();
  await expect(page.getByText(/Status: Wersja robocza,/)).toBeVisible();

  const monthIso = iso(new Date(now.getFullYear(), now.getMonth(), 1));
  const view = await (await page.request.get(`/api/workspace/sites/${siteId}/schedule/${monthIso}`)).json();
  const tomorrow = iso(new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1));
  const target = view.assignments.find(
    (a: { start_datetime: string; role: string }) => a.role === "PRIMARY" && a.start_datetime.slice(0, 10) >= tomorrow,
  );
  expect(target, "the accepted schedule has a future PRIMARY service").toBeTruthy();
  const day = target.start_datetime.slice(0, 10);
  const expected = `Naruszenie: zwolnienie lekarskie — ${target.employee_display_name}; ${day.slice(8, 10)}.${day.slice(5, 7)}.`;
  const banner = page.locator('[data-diag-element="month-warnings"]');

  const l4 = { site_id: siteId, availability_id: `L4-${uid()}`, kind: "SICK_LEAVE", start_date: day, end_date: day };
  expect((await page.request.post(`/api/workspace/employees/${target.employee_id}/availability`, { data: l4 })).status()).toBe(204);
  await page.reload();
  await openSite(page, siteName);
  await openMonthlyPlanning(page);
  await expect(banner).toContainText(expected);

  expect(
    (await page.request.patch(`/api/workspace/employees/${target.employee_id}/availability/${l4.availability_id}`, {
      data: { site_id: siteId, kind: "SICK_LEAVE", start_date: day, end_date: day, active: false },
    })).status(),
  ).toBe(204);
  await page.reload();
  await openSite(page, siteName);
  await openMonthlyPlanning(page);
  await expect(page.getByText(expected)).toHaveCount(0);
});
