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
