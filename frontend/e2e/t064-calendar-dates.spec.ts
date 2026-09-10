// ROTA-T064 (brief.md section 10): minimal real-backend E2E coverage for
// the calendar/date surface -- no page.clock, no fake Date.now(), no
// system-clock manipulation anywhere in this file (brief.md section 5/9,
// T64-01/T64-14): a real future month is reached through real navigation.
import { expect, test } from "@playwright/test";
import { createSite } from "./helpers";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

async function openCalendarModal(page: import("@playwright/test").Page) {
  await page.locator('button[title="Kalendarz (dni robocze i święta)"]').click();
}

async function addLocalEmployee(page: import("@playwright/test").Page, name: string) {
  await page.locator('[data-diag-action="roster-add-open"]').click();
  await page.locator('input[placeholder="np. Jan Kowalski"]').fill(name);
  await page.locator('[data-diag-action="add-person-submit"]').click();
  await expect(page.getByRole("heading", { name: "Godziny docelowe" })).toBeVisible();
}

test.describe("T064: calendar month generation", () => {
  test("T64-01/05/06: navigate to a future month, generate, reload, full month persists", async ({ page }) => {
    const siteName = `T064CAL-${uid()}`;
    await createSite(page, siteName);
    await openCalendarModal(page);

    // Real navigation to next month -- no fake clock. Today (per system
    // reminder in this session) is 2026-09-10, so "next" reaches October.
    await page.locator('[data-diag-action="calendar-next-month"]').click();
    await expect(page.locator(".modal h2")).toContainText("październik");

    await page.getByRole("button", { name: /Wygeneruj kalendarz na miesiąc/ }).click();
    await expect(page.locator(".calendar-day-unconfigured")).toHaveCount(0);
    const totalCells = await page.locator(".calendar-grid .calendar-day").count();
    expect(totalCells).toBeGreaterThanOrEqual(28); // any real month, generous lower bound

    await page.getByRole("button", { name: "Zamknij" }).click();
    await page.reload();
    await openCalendarModal(page);
    await page.locator('[data-diag-action="calendar-next-month"]').click();
    await expect(page.locator(".calendar-day-unconfigured")).toHaveCount(0);
  });

  test("T64-04: manual correction survives regenerate (fill-missing-only)", async ({ page }) => {
    const siteName = `T064CAL-${uid()}`;
    await createSite(page, siteName);
    await openCalendarModal(page);
    await page.locator('[data-diag-action="calendar-next-month"]').click();
    await page.getByRole("button", { name: /Wygeneruj kalendarz na miesiąc/ }).click();
    await expect(page.locator(".calendar-day-unconfigured")).toHaveCount(0);

    // Toggle the first generated day's holiday state by hand -- whatever
    // the library said, the opposite is now the coordinator's own
    // deliberate correction.
    const firstDay = page.locator(".calendar-grid .calendar-day").first();
    const classBefore = (await firstDay.getAttribute("class")) ?? "";
    await firstDay.click();
    await expect(page.locator(".calendar-grid .calendar-day").first()).not.toHaveClass(classBefore);
    const classAfterManualEdit = (await page.locator(".calendar-grid .calendar-day").first().getAttribute("class")) ?? "";

    // Regenerate: fill-missing-only must never revert this.
    await page.getByRole("button", { name: /Wygeneruj kalendarz na miesiąc/ }).click();
    await expect(page.locator(".calendar-day-unconfigured")).toHaveCount(0);
    await expect(page.locator(".calendar-grid .calendar-day").first()).toHaveClass(classAfterManualEdit);
  });
});

test.describe("T064: absence date picker and log", () => {
  test("T64-07/08: AddAbsenceForm opens on workingMonth and saves a real local-date range", async ({ page }) => {
    const siteName = `T064ABS-${uid()}`;
    const empName = `${siteName}-Emp`;
    await createSite(page, siteName);
    await openCalendarModal(page);
    await page.getByRole("button", { name: /Wygeneruj kalendarz na miesiąc/ }).click();
    await expect(page.locator(".calendar-day-unconfigured")).toHaveCount(0);
    await page.getByRole("button", { name: "Zamknij" }).click();

    await page.getByText(siteName, { exact: true }).click();
    await page.locator('[data-diag-action="room-nav-control-panel"]').click();
    await expect(page.getByRole("heading", { name: "Panel sterowania" })).toBeVisible();
    await addLocalEmployee(page, empName);

    await page.getByRole("button", { name: "+ Zgłoś nieobecność" }).click();
    // The picker's own month grid must already show workingMonth (today's
    // real month, 2026-09) without any extra navigation -- day 15 is a
    // real day that exists in every month, safe to assert on.
    await expect(page.locator('[data-day="2026-09-15"]')).toBeVisible();

    await page.locator('[data-day="2026-09-05"]').click();
    await page.locator('[data-day="2026-09-08"]').click();
    await expect(page.getByText("Wybrany zakres: 2026-09-05 – 2026-09-08")).toBeVisible();

    await page.getByRole("button", { name: "Zgłoś", exact: true }).click();
    await expect(page.getByText("Ogólna niedostępność — od 2026-09-05 do 2026-09-08")).toBeVisible();
  });

  test("T64-09/10: AbsenceLog shows only records intersecting workingMonth, sorted", async ({ page }) => {
    const siteName = `T064LOG-${uid()}`;
    const empName = `${siteName}-Emp`;
    await createSite(page, siteName);
    await openCalendarModal(page);
    await page.getByRole("button", { name: /Wygeneruj kalendarz na miesiąc/ }).click();
    await expect(page.locator(".calendar-day-unconfigured")).toHaveCount(0);
    await page.getByRole("button", { name: "Zamknij" }).click();

    await page.getByText(siteName, { exact: true }).click();
    await page.locator('[data-diag-action="room-nav-control-panel"]').click();
    await addLocalEmployee(page, empName);

    // Record A: entirely inside the current month (2026-09) -- must show.
    await page.getByRole("button", { name: "+ Zgłoś nieobecność" }).click();
    await page.locator('[data-day="2026-09-05"]').click();
    await page.locator('[data-day="2026-09-08"]').click();
    await page.getByRole("button", { name: "Zgłoś", exact: true }).click();
    await expect(page.getByText("Ogólna niedostępność — od 2026-09-05 do 2026-09-08")).toBeVisible();

    // Record B: starts the month before and ends inside the current month
    // (spans the boundary) -- must also show (T64-09).
    await page.getByRole("button", { name: "+ Zgłoś nieobecność" }).click();
    await page.locator('[data-diag-element="absence-range-picker"] button[aria-label*="Previous"]').click();
    await page.locator('[data-day="2026-08-25"]').click();
    await page.locator('[data-diag-element="absence-range-picker"] button[aria-label*="Next"]').click();
    await page.locator('[data-day="2026-09-02"]').click();
    await page.getByRole("button", { name: "Zgłoś", exact: true }).click();
    await expect(page.getByText("Ogólna niedostępność — od 2026-08-25 do 2026-09-02")).toBeVisible();

    // Record C: entirely two months ahead (2026-11) -- must NOT show while
    // workingMonth is still 2026-09 (T64-10).
    await page.getByRole("button", { name: "+ Zgłoś nieobecność" }).click();
    await page.locator('[data-diag-element="absence-range-picker"] button[aria-label*="Next"]').click();
    await page.locator('[data-diag-element="absence-range-picker"] button[aria-label*="Next"]').click();
    await page.locator('[data-day="2026-11-10"]').click();
    await page.locator('[data-day="2026-11-12"]').click();
    await page.getByRole("button", { name: "Zgłoś", exact: true }).click();
    await expect(page.getByText(/2026-11-10/)).toHaveCount(0);

    // Deterministic order: A (2026-09-05) after B (2026-08-25).
    const items = page.locator(".absence-log-item");
    await expect(items).toHaveCount(2);
    await expect(items.nth(0)).toContainText("2026-08-25");
    await expect(items.nth(1)).toContainText("2026-09-05");
  });
});
