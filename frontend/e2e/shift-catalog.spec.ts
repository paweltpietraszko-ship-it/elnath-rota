// ROTA-T030 (tasks/ROTA-T030/brief.md section 8, T30-06/T30-07): E2E
// coverage for Panel sterowania -> Obiekt. Backend contract (compute,
// validation, hidden-field preservation, audit trail) is covered by
// tests/test_t030_shift_catalog_api.py -- this file only exercises the
// draft/save/reload UI loop against the real dev build + real backend.
import { test, expect } from "@playwright/test";
import { createSite, openSite } from "./helpers";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

async function openObiektTab(page: import("@playwright/test").Page) {
  await page.locator('[data-diag-action="control-panel-tab-obiekt"]').click();
  await expect(page.locator(".create-panel").first()).toBeVisible();
}

test("add a shift, save, reload shows it persisted", async ({ page }) => {
  const siteName = `SHIFT-SITE-${uid()}`;
  await createSite(page, siteName, `SHIFT-PROF-${uid()}`);
  await openSite(page, siteName);
  await openObiektTab(page);

  // catalog starts empty -> component seeds one blank default row
  const row = page.locator(".create-panel").first();
  await row.getByLabel("Potrzebnych osób").fill("3");

  await page.locator('[data-diag-action="shift-catalog-save"]').click();
  await expect(page.getByText("Zapisano.")).toBeVisible();

  await page.reload();
  await openSite(page, siteName);
  await openObiektTab(page);
  await expect(page.locator(".create-panel").first().getByLabel("Potrzebnych osób")).toHaveValue("3");
});

test("edit an existing shift and reload reflects the edit", async ({ page }) => {
  const siteName = `SHIFT-EDIT-${uid()}`;
  await createSite(page, siteName, `SHIFT-EDIT-PROF-${uid()}`);
  await openSite(page, siteName);
  await openObiektTab(page);

  await page.locator('[data-diag-action="shift-catalog-save"]').click();
  await expect(page.getByText("Zapisano.")).toBeVisible();

  const row = page.locator(".create-panel").first();
  await row.getByLabel("Koniec").selectOption("14:00");
  await page.locator('[data-diag-action="shift-catalog-save"]').click();
  await expect(page.getByText("Zapisano.")).toBeVisible();

  await page.reload();
  await openSite(page, siteName);
  await openObiektTab(page);
  await expect(page.locator(".create-panel").first().getByLabel("Koniec")).toHaveValue("14:00");
});

test("delete one of two rows; the last remaining row is protected", async ({ page }) => {
  const siteName = `SHIFT-DEL-${uid()}`;
  await createSite(page, siteName, `SHIFT-DEL-PROF-${uid()}`);
  await openSite(page, siteName);
  await openObiektTab(page);

  await page.locator('[data-diag-action="shift-catalog-add-row"]').click();
  await expect(page.locator(".create-panel")).toHaveCount(2);

  page.once("dialog", (d) => d.accept());
  await page.locator(".create-panel").nth(1).getByRole("button", { name: "Usuń" }).click();
  await expect(page.locator(".create-panel")).toHaveCount(1);

  await expect(page.locator(".create-panel").first().getByRole("button", { name: "Usuń" })).toBeDisabled();
});

test("save error preserves the draft and shows no false success", async ({ page }) => {
  const siteName = `SHIFT-ERR-${uid()}`;
  await createSite(page, siteName, `SHIFT-ERR-PROF-${uid()}`);
  await openSite(page, siteName);
  await openObiektTab(page);

  await page.route("**/shift-catalog", async (route) => {
    if (route.request().method() === "PUT") {
      await route.fulfill({ status: 400, contentType: "application/json", body: JSON.stringify({ detail: "boom" }) });
    } else {
      await route.continue();
    }
  });

  const row = page.locator(".create-panel").first();
  await row.getByLabel("Potrzebnych osób").fill("5");
  await page.locator('[data-diag-action="shift-catalog-save"]').click();

  await expect(page.getByText("boom")).toBeVisible();
  await expect(page.getByText("Zapisano.")).toHaveCount(0);
  await expect(row.getByLabel("Potrzebnych osób")).toHaveValue("5");
});
