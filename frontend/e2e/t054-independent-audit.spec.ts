import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

import { createSite, openSite } from "./helpers";


const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "..", "..");
const python = path.join(repoRoot, ".venv", "Scripts", "python.exe");
const e2eDb = path.join(repoRoot, "rota_e2e.db");


test("T54-03: Szukaj dalej asks before replacing a persisted preview", async ({ page }) => {
  const siteName = `T054-CONFIRM-${Math.random().toString(36).slice(2, 10)}`;
  await createSite(page, siteName);
  await openSite(page, siteName);
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();

  await page.locator('[data-diag-action="plan-month-first"]').click();
  await expect(page.locator('[data-diag-action="reject-plan-preview"]')).toBeVisible();

  // optimization_complete=false is a normal, supported FEASIBLE result.
  // Keep the real PLAN/persisted candidates and alter only that persisted
  // metadata bit so the existing "Szukaj dalej" path is reachable without
  // depending on solver timing.
  execFileSync(
    python,
    [
      "-c",
      "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('UPDATE plan_previews SET optimization_complete=0'); c.commit(); c.close()",
      e2eDb,
    ],
    { cwd: repoRoot },
  );

  await page.reload();
  await openSite(page, siteName);
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
  const searchAgain = page.locator('[data-diag-action="search-again-incomplete"]');
  await expect(searchAgain).toBeVisible();

  let confirmationSeen = false;
  let replacementPosts = 0;
  page.on("dialog", async (dialog) => {
    confirmationSeen = true;
    await dialog.dismiss();
  });
  page.on("request", (request) => {
    if (request.method() === "POST" && /\/schedule\/[^/]+\/plan$/.test(request.url())) {
      replacementPosts += 1;
    }
  });

  await searchAgain.click();
  await expect.poll(() => ({ confirmationSeen, replacementPosts })).toEqual({
    confirmationSeen: true,
    replacementPosts: 0,
  });
});


test("A-F2: reloaded wide REPLAN continues through the wide endpoint", async ({ page }) => {
  const siteName = `T054-WIDE-${Math.random().toString(36).slice(2, 10)}`;
  await createSite(page, siteName);
  await openSite(page, siteName);
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
  await page.locator('[data-diag-action="plan-month-first"]').click();
  await expect(page.locator('[data-diag-action="reject-plan-preview"]')).toBeVisible();

  // The backend round-trip for a real wide result is covered independently
  // in test_t054_r4_architect_audit.py. Here only the browser dispatch seam
  // is under test, so put that valid persisted metadata state under the UI.
  execFileSync(
    python,
    [
      "-c",
      "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute(\"UPDATE plan_previews SET optimization_complete=0, operation_kind='replan_wide' WHERE rowid=(SELECT max(rowid) FROM plan_previews)\"); c.commit(); c.close()",
      e2eDb,
    ],
    { cwd: repoRoot },
  );

  await page.reload();
  await openSite(page, siteName);
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
  const searchAgain = page.locator('[data-diag-action="search-again-incomplete"]');
  await expect(searchAgain).toBeVisible();

  page.on("dialog", async (dialog) => dialog.accept());
  const wideRequest = page.waitForRequest(
    (request) => request.method() === "POST" && /\/schedule\/[^/]+\/replan\/wider-search$/.test(request.url()),
  );
  await searchAgain.click();
  await wideRequest;
});


test("T54-06: failed replacement save remains visible with its warning", async ({ page }) => {
  const siteName = `T054-SAVE-FAIL-${Math.random().toString(36).slice(2, 10)}`;
  await createSite(page, siteName);
  await openSite(page, siteName);
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();

  await page.locator('[data-diag-action="plan-month-first"]').click();
  await expect(page.locator('[data-diag-action="reject-plan-preview"]')).toBeVisible();

  execFileSync(
    python,
    [
      "-c",
      "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute(\"CREATE TRIGGER audit_t054_reject_preview_update BEFORE UPDATE ON plan_previews BEGIN SELECT RAISE(ABORT, 'audit preview update failure'); END\"); c.commit(); c.close()",
      e2eDb,
    ],
    { cwd: repoRoot },
  );

  page.on("dialog", async (dialog) => dialog.accept());
  const refreshedMonth = page.waitForResponse(
    (response) => /\/schedule\/\d{4}-\d{2}-\d{2}$/.test(response.url())
      && response.request().method() === "GET",
  );
  await page.locator('[data-diag-action="plan-month-recompute"]').click();
  await refreshedMonth;
  await page.waitForTimeout(100);

  await expect(page.getByText(/Ten wynik nie zosta.*zapisany trwale/)).toBeVisible();
});
