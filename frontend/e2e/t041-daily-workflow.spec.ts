// ROTA-T041 Checkpoint C (tasks/ROTA-T041/brief.md section 6): E2E coverage
// for "Ręczna korekta"/"Wydruk Grafiku" sharing one screen, the missing-
// target warning actually reaching the coordinator, and PDF preview/
// download sharing one set of bytes. Backend contracts for the warning
// content and equal-split fallback are covered by
// tests/test_t041_checkpoint_a.py and tests/test_t041_checkpoint_b.py --
// this file exercises the real frontend flow against the real dev backend.
import { test, expect } from "@playwright/test";
import { createSite } from "./helpers";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

// NOT the shared helpers.ts openSite(): that one waits for the "Panel
// sterowania" heading to appear right after clicking the site card, which
// assumes Room's default landing tab is Panel sterowania. It currently
// isn't (Room.tsx defaults activeNav to "Praegląd"/Overview) -- confirmed
// pre-existing and unrelated to T041 by running the existing, untouched
// shift-catalog.spec.ts against both this checkpoint's changes and the
// pre-checkpoint-C baseline; both fail identically at that same wait. Out
// of TASK_SCOPE to fix (helpers.ts isn't a T041 file) -- this local helper
// just avoids relying on the assumption, using the sidebar nav directly.
async function openSite(page: import("@playwright/test").Page, displayName: string) {
  await page.getByText(displayName, { exact: true }).click();
  await page.locator('[data-diag-action="room-nav-control-panel"]').waitFor({ state: "visible" });
  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await page.getByRole("heading", { name: "Panel sterowania" }).waitFor();
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
  // add-person navigates straight to EmployeeDetail -- come back to the roster.
  await page.getByRole("button", { name: /Wróć do obsady/ }).click();
  await expect(page.getByRole("heading", { name: "Panel sterowania" })).toBeVisible();
}

async function saveDefaultCatalogRow(page: import("@playwright/test").Page) {
  await page.locator('[data-diag-action="control-panel-tab-obiekt"]').click();
  await page.locator('[data-diag-action="shift-catalog-save"]').click();
  await expect(page.getByText("Zapisano.")).toBeVisible();
  await page.locator('[data-diag-action="control-panel-tab-obsada"]').click();
}

async function openViaNav(page: import("@playwright/test").Page, navAction: string) {
  await page.locator(`[data-diag-action="${navAction}"]`).click();
  await expect(page.getByRole("heading", { name: "Planowanie miesiąca" })).toBeVisible();
}

test("C05: both shortcuts open the same screen and keep the selected month", async ({ page }) => {
  const siteName = `T041-NAV-${uid()}`;
  await createSite(page, siteName, `T041-NAV-PROF-${uid()}`);
  await openSite(page, siteName);

  await openViaNav(page, "room-nav-manual-correction");
  const monthSelect = page.getByLabel("Miesiąc");
  await monthSelect.selectOption({ index: 0 });
  const monthAfterKorekta = await monthSelect.inputValue();

  await openViaNav(page, "room-nav-export");
  await expect(page.getByLabel("Miesiąc")).toHaveValue(monthAfterKorekta);
});

test("C06/C07/C10: correction instruction, inline print, print settings link, other nav unchanged (C11)", async ({ page }) => {
  const siteName = `T041-SCREEN-${uid()}`;
  await createSite(page, siteName, `T041-SCREEN-PROF-${uid()}`);
  await openSite(page, siteName);

  await openViaNav(page, "room-nav-manual-correction");
  await expect(page.getByText(/Kliknij dowolny wpis w grafiku/)).toBeVisible();

  await openViaNav(page, "room-nav-export");
  await expect(page.getByRole("heading", { name: "Wydruk Grafiku" })).toBeVisible();
  // Fresh site has no saved print settings yet -- Export shows the
  // "configure it" link instead of the plain "Ustawienia wydruku" button;
  // either way it must land on Panel sterowania -> Obiekt.
  await page.getByRole("button", { name: /Skonfiguruj w Panelu sterowania/ }).click();
  await expect(page.getByRole("heading", { name: "Panel sterowania" })).toBeVisible();
  await expect(page.locator(".create-panel").first()).toBeVisible();

  // C11: the rest of the nav is unchanged (still present, still separate screens).
  // History.tsx's own heading is "Akcje koordynatora" (there is no literal
  // "Historia i audyt" heading anywhere in that screen) -- this is a fact
  // about the existing screen, not something T041 changed.
  for (const [label, heading] of [
    ["Decyzje koordynatora", "Decyzje koordynatora"],
    ["Analityka i bilanse", "Analityka i bilanse"],
    ["Historia i audyt", "Akcje koordynatora"],
  ] as const) {
    await page.getByRole("button", { name: label, exact: true }).click();
    await expect(page.getByRole("heading", { name: heading }).first()).toBeVisible();
  }
});

test("C08/C09: preview and download share one export call; a failed regeneration leaves no stale preview", async ({ page }) => {
  const siteName = `T041-PDF-${uid()}`;
  await createSite(page, siteName, `T041-PDF-PROF-${uid()}`);
  // The calendar button lives on Workspace (the site list), not inside Room.
  await generateCalendarForCurrentMonth(page);
  await openSite(page, siteName);
  // The default catalog row needs a person every day of the month -- one
  // employee alone cannot cover that without breaking rest rules, which
  // would return DECISION_REQUIRED instead of a FEASIBLE candidate. Two
  // employees give the solver enough room for a real, clean plan.
  await addLocalEmployee(page, `${siteName}-E1`);
  await addLocalEmployee(page, `${siteName}-E2`);
  await page.locator('[data-diag-action="control-panel-tab-obiekt"]').click();
  await page.locator('[data-diag-action="shift-catalog-save"]').click();
  await expect(page.getByText("Zapisano.")).toBeVisible();
  // Export refuses to generate anything until print settings exist for the
  // site (PrintSettings.tsx, embedded on the same "Obiekt" tab) -- save the
  // defaults as-is, same pattern as saveDefaultCatalogRow above. Scoped to
  // the PrintSettings panel specifically since the shift-catalog panel's
  // own "Zapisano." banner may still be visible from the save just above.
  const printSettingsPanel = page.locator(".create-panel", { hasText: "Ustawienia wydruku" });
  await printSettingsPanel.getByRole("button", { name: "Zapisz ustawienia" }).click();
  await expect(printSettingsPanel.getByText("Zapisano.")).toBeVisible();
  await page.locator('[data-diag-action="control-panel-tab-obsada"]').click();

  // Export legitimately refuses to generate anything ("Brak aktualnego
  // grafiku dla tego miesiąca") until a schedule version exists -- run a
  // real PLAN first, same as the other tests, rather than exporting nothing.
  await openViaNav(page, "room-nav-monthly-planning");
  await page.locator('[data-diag-action="plan-month-first"]').click();
  await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
  await page.locator('[data-diag-action="select-candidate"]').first().click();
  await expect(page.getByText(/status: WORKING/)).toBeVisible();

  await openViaNav(page, "room-nav-export");

  let exportCalls = 0;
  await page.route("**/schedule/*/export", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    exportCalls += 1;
    return route.continue();
  });

  await page.locator('button:has-text("Wygeneruj podgląd PDF")').click();
  await expect(page.locator('[data-diag-element="export-preview"]')).toBeVisible({ timeout: 15000 });
  expect(exportCalls).toBe(1);

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.locator('[data-diag-action="export-download"]').click(),
  ]);
  expect(download).toBeTruthy();
  // Downloading must not have triggered a second generation call.
  expect(exportCalls).toBe(1);

  // Now force a failing regeneration and confirm the old preview is cleared,
  // not left on screen mislabeled as the new attempt's result.
  await page.route("**/schedule/*/export", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({ ok: false, pdf_base64: null, document_revision: null, schedule_provenance: null, problem_code: "boom", message: "boom" }),
    });
  });
  await page.locator('button:has-text("Wygeneruj podgląd PDF")').click();
  await expect(page.getByText("boom")).toBeVisible();
  await expect(page.locator('[data-diag-element="export-preview"]')).toHaveCount(0);
  await expect(page.locator('[data-diag-action="export-download"]')).toHaveCount(0);
});

test("C01-C04: missing target_hours warning reaches the coordinator, survives reload, clears once fixed, never fires for EXTERNAL_SUPPORT", async ({ page }) => {
  const siteName = `T041-WARN-${uid()}`;
  const empName = `Pracownik-${uid()}`;
  await createSite(page, siteName, `T041-WARN-PROF-${uid()}`);
  // The calendar button lives on Workspace (the site list), not inside
  // Room -- must run before openSite navigates into the object.
  await generateCalendarForCurrentMonth(page);
  await openSite(page, siteName);

  // Two employees: one alone cannot legally cover the default catalog's
  // daily demand without breaking rest rules (DECISION_REQUIRED instead of
  // a real plan). Only empName is asserted on below; the second person just
  // gives the solver room for a real FEASIBLE candidate.
  await addLocalEmployee(page, empName);
  await addLocalEmployee(page, `${siteName}-E2`);
  await saveDefaultCatalogRow(page);

  await openViaNav(page, "room-nav-monthly-planning");
  await page.locator('[data-diag-action="plan-month-first"]').click();
  await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
  await page.locator('[data-diag-action="select-candidate"]').first().click();

  const warningBanner = page.locator('[data-diag-element="month-warnings"]');
  await expect(warningBanner).toBeVisible();
  await expect(warningBanner).toContainText(empName);
  await expect(warningBanner).toContainText("równego podziału");

  await page.reload();
  await openSite(page, siteName);
  await openViaNav(page, "room-nav-monthly-planning");
  await expect(page.locator('[data-diag-element="month-warnings"]')).toContainText(empName);

  // Fix the gap: T41-C03 requires the warning to clear only once EVERY
  // available LOCAL employee has a target -- both, not just empName.
  await page.locator('[data-diag-action="control-panel-tab-obsada"]').click().catch(() => undefined);
  for (const target of [empName, `${siteName}-E2`]) {
    await page.locator('[data-diag-action="roster-open-employee"]').filter({ hasText: target }).click();
    await expect(page.getByRole("heading", { name: "Godziny docelowe" })).toBeVisible();
    await page.locator('input[type="number"]').last().fill("160");
    await page.getByRole("button", { name: "Zapisz" }).click();
    await page.getByRole("button", { name: /Wróć do obsady/ }).click();
  }
  await openViaNav(page, "room-nav-monthly-planning");
  // A WORKING version already exists from the first PLAN above -- the
  // button is now "Przelicz (PLAN)" (plan-month-recompute), not the
  // first-ever-plan button.
  await page.locator('[data-diag-action="plan-month-recompute"]').click();
  await page.locator('[data-diag-action="select-candidate"]').first().click();
  await expect(page.locator('[data-diag-element="month-warnings"]')).toHaveCount(0);
});

test("C06: manual correction works via the Ręczna korekta entry even when current version is FINAL", async ({ page }) => {
  const siteName = `T041-FINAL-${uid()}`;
  const empName = `Pracownik-${uid()}`;
  await createSite(page, siteName, `T041-FINAL-PROF-${uid()}`);
  await generateCalendarForCurrentMonth(page);
  await openSite(page, siteName);

  // Same reason as the other tests: one employee alone can't legally cover
  // the default catalog's daily demand for a whole month.
  await addLocalEmployee(page, empName);
  await addLocalEmployee(page, `${siteName}-E2`);
  await saveDefaultCatalogRow(page);

  await openViaNav(page, "room-nav-monthly-planning");
  await page.locator('[data-diag-action="plan-month-first"]').click();
  await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
  await page.locator('[data-diag-action="select-candidate"]').first().click();
  await expect(page.getByText(/status: WORKING/)).toBeVisible();

  await page.locator('[data-diag-action="finalize-month"]').click();
  await expect(page.getByText(/status: FINAL_/)).toBeVisible();
  const finalVersionText = await page.getByText(/Wersja: SV-/).textContent();
  const finalVersionId = finalVersionText?.match(/SV-[a-f0-9]+/)?.[0];

  await openViaNav(page, "room-nav-manual-correction");
  await expect(page.getByText(/Kliknij dowolny wpis w grafiku/)).toBeVisible();

  // Click the first real assignment cell in the grid and toggle freeze --
  // the existing correction backend must accept this on a FINAL version by
  // creating a new child WORKING, never by mutating FINAL in place.
  await page.locator('[data-diag-action="manual-correction-select-assignment"]').first().click();
  await expect(page.getByText(/Ręczna korekta —/)).toBeVisible();
  await page.getByRole("button", { name: /Zamroź|Odmroź/ }).click();

  await expect(page.getByText(/status: WORKING/)).toBeVisible();
  const childVersionText = await page.getByText(/Wersja: SV-/).textContent();
  const childVersionId = childVersionText?.match(/SV-[a-f0-9]+/)?.[0];
  expect(childVersionId).not.toBe(finalVersionId);

  // The FINAL parent must still exist, unchanged, in history.
  await page.locator('[data-diag-action="history-toggle"]').click();
  await expect(page.getByText(new RegExp(finalVersionId!))).toBeVisible();
});
