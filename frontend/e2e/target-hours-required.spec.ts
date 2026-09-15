// ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE (brief.md TASK_SCOPE):
// end-to-end coverage for the target-hours gate's UI contract --
// PLAN/REPLAN refuse to run and show the missing-employees blocker
// instead, and (Codex audit R3-01/R4) a stale unaccepted plan_preview
// never resurrects itself over that blocker on reload.
import { test, expect } from "@playwright/test";
import { openSite } from "./helpers";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

// OCHRONA (not helpers.ts's own createSite, which is ORDINARY and would
// also require a role catalog before any employee can be added --
// unrelated to what this file tests).
async function createOchronaSite(page: import("@playwright/test").Page, displayName: string) {
  await page.goto("/");
  await page.locator('[data-diag-action="create-site-open"]').click();
  await page.locator('input[placeholder="np. NORDPLAST II"]').fill(displayName);
  await page.locator('[data-diag-action="create-site-submit"]').click();
  await page.getByText(displayName, { exact: true }).waitFor();
}

async function generateCalendarForCurrentMonth(page: import("@playwright/test").Page) {
  await page.locator('button[title="Kalendarz (dni robocze i święta)"]').click();
  await page.getByRole("button", { name: /Wygeneruj kalendarz na miesiąc/ }).click();
  await page.locator(".calendar-day-unconfigured").first().waitFor({ state: "detached" }).catch(() => undefined);
  await page.getByRole("button", { name: "Zamknij" }).click();
}

// Adds a LOCAL employee via "+ Dodaj osobę"; onAdded navigates straight to
// the new employee's Karta pracownika (ControlPanel.tsx's own AddPersonPanel
// behavior), which is where the caller sets (or deliberately skips) a
// target_hours before returning to the roster. Mirrors the proven flow
// frontend/e2e/t041-daily-workflow.spec.ts already uses for this exact
// screen sequence.
async function addLocalEmployee(page: import("@playwright/test").Page, displayName: string) {
  await page.locator('[data-diag-action="roster-add-open"]').click();
  await page.locator('input[placeholder="np. Jan Kowalski"]').fill(displayName);
  await page.locator('[data-diag-action="add-person-submit"]').click();
  await expect(page.getByRole("heading", { name: displayName })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Godziny docelowe" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Wróć do obsady/ })).toBeVisible();
}

async function setTargetHours(page: import("@playwright/test").Page, hours: number) {
  await page.locator('input[type="number"]').last().fill(String(hours));
  await page.getByRole("button", { name: "Zapisz" }).click();
  // The "ustawić wszystkim?" proposal always follows a successful save --
  // declined here so it never affects any other employee at this site.
  // "Nie" is scoped to the prompt itself -- unscoped, it substring-matches
  // unrelated nav buttons too ("Planowa-nie- miesiąca", "+ Zgłoś -nie-
  // obecność").
  const prompt = page.locator('[data-diag-action="target-hours-apply-all-prompt"]');
  await prompt.waitFor();
  await prompt.getByRole("button", { name: "Nie", exact: true }).click();
}

async function backToRoster(page: import("@playwright/test").Page) {
  // The persistent side-nav item, not the in-page "Wróć do obsady" button --
  // reliable regardless of how much content has accumulated on the current
  // Karta pracownika (absence log, restriction history, etc. all grow the
  // page across this file's multiple employees).
  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await expect(page.getByRole("heading", { name: "Panel sterowania" })).toBeVisible();
}

async function openMonthlyPlanning(page: import("@playwright/test").Page) {
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
  await expect(page.getByRole("heading", { name: "Planowanie miesiąca" })).toBeVisible();
}

test("stale plan_preview never hides the missing-target-hours blocker (Codex audit R3-01)", async ({ page }) => {
  // "Chcę inny wariant (REPLAN)" below goes through confirmReplacePreview
  // (MonthlyPlanning.tsx), a real window.confirm() once a persisted
  // preview exists -- Playwright auto-dismisses confirm() by default,
  // which would silently no-op the click.
  page.on("dialog", (dialog) => dialog.accept());

  const siteName = `TH-SITE-${uid()}`;
  await createOchronaSite(page, siteName);
  await generateCalendarForCurrentMonth(page);
  await openSite(page, siteName);

  // Two employees, both with a target -- a lone one covering every day
  // would trip the unrelated HARD max-two-consecutive-shifts rule (same
  // fixture pattern used throughout tests/, e.g. test_t019b.py).
  await addLocalEmployee(page, "Anna Testowa");
  await setTargetHours(page, 100);
  await backToRoster(page);
  await addLocalEmployee(page, "Bartek Testowy");
  await setTargetHours(page, 100);
  await backToRoster(page);

  await openMonthlyPlanning(page);
  await page.locator('[data-diag-action="plan-month-first"]').click();
  await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
  await expect(page.getByText("Niezatwierdzony wynik PLAN")).toBeVisible();

  // A third employee joins with NO target_hours yet -- the exact
  // "existing plan_preview + newly-incomplete roster" shape from the
  // Codex audit's own live repro.
  await backToRoster(page);
  await addLocalEmployee(page, "Jan Testowy");
  await backToRoster(page);

  await openMonthlyPlanning(page);
  await page.locator('[data-diag-action="replan-fresh-again"]').click();

  // A real REPLAN round-trip (network + gate check), not instantaneous --
  // the default 5s expect timeout is too tight for it.
  const blocker = page.locator('[data-diag-action="target-hours-required-banner"]');
  await expect(blocker).toBeVisible({ timeout: 15000 });
  await expect(blocker).toContainText("Jan Testowy");
  // R3-01: this used to reappear here, silently replacing the blocker.
  await expect(page.getByText("Niezatwierdzony wynik PLAN")).not.toBeVisible();
});

test("apply-to-all propagates one target_hours to every active LOCAL employee", async ({ page }) => {
  const siteName = `TH-ALL-${uid()}`;
  await createOchronaSite(page, siteName);
  await openSite(page, siteName);

  await addLocalEmployee(page, "Celina Testowa");
  await page.locator('input[type="number"]').last().fill("120");
  await page.getByRole("button", { name: "Zapisz" }).click();
  await page.locator('[data-diag-action="target-hours-apply-all-prompt"]').waitFor();
  await page.locator('[data-diag-action="target-hours-apply-all-yes"]').click();
  await expect(page.locator('[data-diag-action="target-hours-apply-all-prompt"]')).not.toBeVisible();

  await backToRoster(page);
  await addLocalEmployee(page, "Damian Testowy");
  // Damian never got his own save -- apply-to-all above ran before he even
  // existed, so PLAN must still see him as missing a target.
  await backToRoster(page);
  await openMonthlyPlanning(page);
  await page.locator('[data-diag-action="plan-month-first"]').click();
  const blocker = page.locator('[data-diag-action="target-hours-required-banner"]');
  await expect(blocker).toBeVisible({ timeout: 15000 });
  await expect(blocker).toContainText("Damian Testowy");
});
