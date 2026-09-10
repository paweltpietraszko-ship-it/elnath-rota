// Independent ROTA-T064 audit reproducer. During audit this test was inserted
// temporarily into frontend/e2e/t064-calendar-dates.spec.ts so it ran under
// the existing real-backend Playwright configuration; the product test was
// restored unchanged afterwards.
import { expect, test } from "@playwright/test";
import { createSite } from "../../../../frontend/e2e/helpers";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

async function addLocalEmployee(page: import("@playwright/test").Page, name: string) {
  await page.locator('[data-diag-action="roster-add-open"]').click();
  await page.locator('input[placeholder="np. Jan Kowalski"]').fill(name);
  await page.locator('[data-diag-action="add-person-submit"]').click();
  await expect(page.getByRole("heading", { name: "Godziny docelowe" })).toBeVisible();
}

test("T64-11: an already-open picker follows workingMonth", async ({ page }) => {
  const siteName = `T064MONTH-${uid()}`;
  await createSite(page, siteName);
  await page.getByText(siteName, { exact: true }).click();
  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await addLocalEmployee(page, `${siteName}-Emp`);

  await page.getByRole("button", { name: "+ Zgłoś nieobecność" }).click();
  const workingMonth = page.locator('[data-diag-element="room-working-month"]');
  const initial = await workingMonth.inputValue();
  const [year, month] = initial.split("-").map(Number);
  const nextDate = new Date(year, month, 1);
  const next = `${nextDate.getFullYear()}-${String(nextDate.getMonth() + 1).padStart(2, "0")}`;
  await expect(page.locator(`[data-day="${initial}-15"]`)).toBeVisible();

  await workingMonth.fill(next);
  await expect(page.locator(`[data-day="${next}-15"]`)).toBeVisible();
});
