// ROTA-T042 Checkpoint A (tasks/ROTA-T042/brief.md section 2, matrix
// T42-A01..A04): confirms Analytics, Export, Overview and MonthlyPlanning
// resolve "today" from the coordinator's local calendar date, not from
// new Date().toISOString() (which reports the previous UTC day between
// local midnight and the UTC offset). Backend is untouched by this
// checkpoint; this is purely a frontend clock/timezone test.
import { test, expect } from "@playwright/test";
import { createSite } from "./helpers";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

// NOT the shared helpers.ts openSite(): that one waits for the "Panel
// sterowania" heading right after clicking the site card, which assumes
// Room's default landing tab is Panel sterowania -- it currently isn't
// (Room.tsx defaults activeNav to "Przegląd"/Overview). Same pre-existing,
// out-of-scope mismatch already documented and worked around in
// t041-daily-workflow.spec.ts.
async function openSite(page: import("@playwright/test").Page, displayName: string) {
  await page.getByText(displayName, { exact: true }).click();
  await page.locator('[data-diag-action="room-nav-overview"]').waitFor({ state: "visible" });
}

// assemble_planning_state requires a CalendarDay row for every date in the
// target month before PLAN can run -- the frozen clock's target month is
// September 2026, which has no calendar seeded yet.
async function generateCalendarForCurrentMonth(page: import("@playwright/test").Page) {
  await page.locator('button[title="Kalendarz (dni robocze i święta)"]').click();
  await page.getByRole("button", { name: /Wygeneruj kalendarz na miesiąc/ }).click();
  await page.locator(".calendar-day-unconfigured").first().waitFor({ state: "detached" }).catch(() => undefined);
  await page.getByRole("button", { name: "Zamknij" }).click();
}

test.describe("T042 Checkpoint A -- local date across the UTC boundary", () => {
  test.use({ timezoneId: "Europe/Warsaw" });

  test("T42-A01/A02/A03: 22:30 UTC on 2026-08-31 is already 2026-09-01 in Warsaw", async ({ page }) => {
    await page.clock.install({ time: new Date("2026-08-31T22:30:00Z") });

    const displayName = `T042A-${uid()}`;
    await createSite(page, displayName);
    await generateCalendarForCurrentMonth(page);

    // T42-A02: Room lands on "Przegląd"/Overview by default, so its
    // /overview request fires on mount -- register the listener before the
    // click that opens the site, not after.
    const overviewRequest = page.waitForRequest((r) => r.url().includes("/overview?month="));
    await openSite(page, displayName);
    const req = await overviewRequest;
    expect(new URL(req.url()).searchParams.get("month")).toBe("2026-09-01");

    // T42-A02: Analytics defaults its month picker to September.
    await page.locator('[data-diag-action="room-nav-analytics"]').click();
    await expect(page.locator('input[type="month"]')).toHaveValue("2026-09");

    // T42-A02: Export defaults its month picker to September. Its month
    // input only renders once print settings exist for the site (fresh
    // sites show a "configure it" banner instead), so save minimal print
    // settings first. Unlike t041-daily-workflow.spec.ts's C08/C09 test,
    // no shift-catalog-save here: PrintSettings' work-code rows come from
    // the static FROZEN_WORK_CODE_HOURS table, not from actual configured
    // demands, and saving a real D-shift demand with no roster to cover it
    // would push PLAN below into DECISION_REQUIRED instead of a trivial
    // FEASIBLE with zero candidates -- out of scope for this date-only check.
    await page.locator('[data-diag-action="room-nav-control-panel"]').click();
    await page.locator('[data-diag-action="control-panel-tab-obiekt"]').click();
    const printSettingsPanel = page.locator(".create-panel", { hasText: "Ustawienia wydruku" });
    const d1Row = printSettingsPanel.locator("tr", { hasText: "D1" });
    await d1Row.locator('input[type="time"]').first().fill("06:00");
    await d1Row.locator('input[type="time"]').nth(1).fill("18:00");
    await printSettingsPanel.getByRole("button", { name: "Zapisz ustawienia" }).click();
    await expect(printSettingsPanel.getByText("Zapisano.")).toBeVisible();

    await page.locator('[data-diag-action="room-nav-export"]').click();
    await expect(page.locator('input[type="month"]')).toHaveValue("2026-09");

    // T42-A03: MonthlyPlanning defaults to September and its REPLAN
    // cutover date defaults to 2026-09-01, not 2026-08-31.
    await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
    await expect(page.getByRole("heading", { name: "Planowanie miesiąca" })).toBeVisible();
    // ROTA-T053: MonthlyPlanning no longer has its own month picker -- it
    // reads the single Room-level "Miesiąc roboczy" input already asserted
    // above, which stays September across every screen.
    await expect(page.locator('input[type="month"]')).toHaveValue("2026-09");

    await page.locator('[data-diag-action="plan-month-first"]').click();
    await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
    await page.locator('[data-diag-action="select-candidate"]').first().click();
    await expect(page.getByText(/status: WORKING/)).toBeVisible();

    await page.locator('[data-diag-action="replan-open"]').click();
    await expect(page.getByLabel("Data odcięcia (REPLAN)")).toHaveValue("2026-09-01");
  });

  test("T42-A04: an ordinary midday moment still resolves the correct local date", async ({ page }) => {
    await page.clock.install({ time: new Date("2026-09-15T12:00:00Z") });

    const displayName = `T042A4-${uid()}`;
    await createSite(page, displayName);
    await openSite(page, displayName);

    await page.locator('[data-diag-action="room-nav-analytics"]').click();
    await expect(page.locator('input[type="month"]')).toHaveValue("2026-09");
  });
});
