import { expect, test } from "@playwright/test";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

async function createOchronaSite(page: import("@playwright/test").Page, displayName: string) {
  await page.goto("/");
  await page.locator('[data-diag-action="create-site-open"]').click();
  await page.locator('input[placeholder="np. NORDPLAST II"]').fill(displayName);
  await page.locator('[data-diag-action="create-site-submit"]').click();
  await page.getByText(displayName, { exact: true }).waitFor();
}

test("absence range requires a deliberate second click, including one-day range", async ({ page }) => {
  const siteName = `AUDIT-ABS-${uid()}`;
  await createOchronaSite(page, siteName);

  await page.locator('button[title="Kalendarz (dni robocze i święta)"]').click();
  await page.getByRole("button", { name: /Wygeneruj kalendarz na miesiąc/ }).click();
  await expect(page.locator(".calendar-day-unconfigured")).toHaveCount(0);
  await page.getByRole("button", { name: "Zamknij" }).click();

  await page.getByText(siteName, { exact: true }).click();
  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await page.locator('[data-diag-action="roster-add-open"]').click();
  await page.locator('input[placeholder="np. Jan Kowalski"]').fill(`${siteName}-Emp`);
  await page.locator('[data-diag-action="add-person-submit"]').click();

  await page.getByRole("button", { name: "+ Zgłoś nieobecność" }).click();
  const submit = page.getByRole("button", { name: "Zgłoś", exact: true });
  await expect(submit).toBeDisabled();

  const visibleDays = page.locator('[data-diag-element="absence-range-picker"] [data-day]:not([data-hidden="true"])');
  const day = visibleDays.first();
  const isoDay = await day.getAttribute("data-day");
  expect(isoDay).toMatch(/^\d{4}-\d{2}-\d{2}$/);

  await day.click();
  await expect(page.getByText("Kliknij datę końcową (tę samą, jeśli to jeden dzień).")).toBeVisible();
  await expect(submit).toBeDisabled();

  await day.click();
  await expect(page.getByText(`Wybrany zakres: ${isoDay} – ${isoDay}`)).toBeVisible();
  await expect(submit).toBeEnabled();

  const otherDay = visibleDays.nth(1);
  const otherIsoDay = await otherDay.getAttribute("data-day");
  expect(otherIsoDay).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  await otherDay.click();
  await expect(submit).toBeDisabled();
  await day.click();
  const [from, to] = [isoDay!, otherIsoDay!].sort();
  await expect(page.getByText(`Wybrany zakres: ${from} – ${to}`)).toBeVisible();
  await expect(submit).toBeEnabled();
});
