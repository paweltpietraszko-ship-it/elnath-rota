import { expect, test } from "@playwright/test";
import { createSite } from "./helpers";

const STORAGE_KEY = "elnath-rota-working-month";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

async function openRoom(page: import("@playwright/test").Page, siteName: string) {
  await page.getByText(siteName, { exact: true }).click();
  await page.locator('[data-diag-action="room-nav-overview"]').waitFor({ state: "visible" });
}

test("T53-AUD-01: one month drives real screens, employee context, reload and another site", async ({ page }) => {
  const siteA = `T53-A-${uid()}`;
  const siteB = `T53-B-${uid()}`;
  const employee = `T53-E-${uid()}`;
  await createSite(page, siteA);
  await createSite(page, siteB);
  await openRoom(page, siteA);

  const monthInput = page.locator('[data-diag-element="room-working-month"]');
  await monthInput.fill("2027-02");

  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await page.locator('[data-diag-action="roster-add-open"]').click();
  await page.locator('input[placeholder="np. Jan Kowalski"]').fill(employee);
  const employeeMonthRequest = page.waitForRequest(
    (r) => r.url().includes("/target-hours?month=2027-02-01") && r.method() === "GET",
  );
  await page.locator('[data-diag-action="add-person-submit"]').click();
  await employeeMonthRequest;
  await expect(page.getByRole("heading", { name: "Godziny docelowe" })).toBeVisible();
  await page.getByRole("button", { name: /Wróć do obsady/ }).click();

  const planningRequest = page.waitForRequest(
    (r) => r.url().includes("/schedule/2027-02-01") && r.method() === "GET",
  );
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
  await planningRequest;

  const analyticsRequest = page.waitForRequest(
    (r) => r.url().includes("/analytics?month=2027-02-01") && r.method() === "GET",
  );
  await page.locator('[data-diag-action="room-nav-analytics"]').click();
  await analyticsRequest;

  await page.reload();
  await openRoom(page, siteA);
  await expect(page.locator('[data-diag-element="room-working-month"]')).toHaveValue("2027-02");

  await page.locator('[data-diag-action="breadcrumb-back"]').click();
  await openRoom(page, siteB);
  await expect(page.locator('[data-diag-element="room-working-month"]')).toHaveValue("2027-02");
});

test("T53-AUD-02: a calendar-looking but impossible stored month fails soft", async ({ page }) => {
  await page.addInitScript(({ key }) => localStorage.setItem(key, "2026-99"), { key: STORAGE_KEY });
  const siteName = `T53-BAD-${uid()}`;
  await createSite(page, siteName);
  await openRoom(page, siteName);

  const expected = await page.evaluate(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  });
  await expect(page.locator('[data-diag-element="room-working-month"]')).toHaveValue(expected);
});

test("T53-AUD-03: print has no second editable source for the same period", async ({ page }) => {
  const siteName = `T53-PRINT-${uid()}`;
  await createSite(page, siteName);
  await openRoom(page, siteName);

  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await page.locator('[data-diag-action="control-panel-tab-obiekt"]').click();
  const printSettings = page.locator(".create-panel", { hasText: "Ustawienia wydruku" });
  const d1Row = printSettings.locator("tr", { hasText: "D1" });
  await d1Row.locator('input[type="time"]').first().fill("06:00");
  await d1Row.locator('input[type="time"]').nth(1).fill("18:00");
  await printSettings.getByRole("button", { name: "Zapisz ustawienia" }).click();
  await expect(printSettings.getByText("Zapisano.")).toBeVisible();

  await page.locator('[data-diag-action="room-nav-export"]').click();
  await expect(page.getByRole("heading", { name: "Wydruk Grafiku" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Ustawienia wydruku" })).toBeVisible();
  await expect(page.getByLabel("Etykieta okresu na wydruku")).toHaveCount(0);
});
