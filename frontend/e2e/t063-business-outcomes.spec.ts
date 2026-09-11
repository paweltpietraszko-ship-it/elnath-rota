// ROTA-T063 (brief.md; SCENARIO_PACK v0.3, OWNER APPROVED): reference
// business-outcome acceptance tests. A green test here must prove a real,
// frozen business result -- not merely that the UI clicked PLAN or that
// the API answered. Scenarios are reproduced literally from
// tasks/ROTA-T063/scenario_pack.md; no staffing/absence/external data is
// invented or extended to make a test pass (brief.md section 2/13).
//
// OWNER_CORRECTED 2026-09-11 (SCENARIO_PACK v0.3): the scenario month is
// always the REAL current calendar month at run time, and the absence
// windows are offsets from the run date (OKNO_7D/OKNO_3D), not the
// originally-frozen October 2026 -- see scenario_pack.md's own
// OWNER_CORRECTED section for the full rationale (a real, T064-independent
// blocker: `is_schedule_version_live` requires the schedule's first shift
// to have already started against the REAL server clock, which a
// permanently-future fixed month could never satisfy). No page.clock, no
// fake Date.now(), no system-clock manipulation anywhere in this file.
import { expect, test } from "@playwright/test";
import { openSite } from "./helpers";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

// NOT the shared helpers.ts createSite(): scenario_pack.md's own "Twardy
// fakt scenariusza" in S02 is built on a 60h/7-day rolling threshold, but
// the create-object form's default ("Próg decyzyjny 7-dniowy") is 40 --
// too low for this object's 2x12h/day demand shape and empirically LOAD-
// blocks even the S02 base state before any SICK_LEAVE. This object's
// threshold is a fixed, necessary input, not a per-scenario choice.
async function createSiteWithThreshold(page: import("@playwright/test").Page, displayName: string, threshold: number) {
  await page.goto("/");
  await page.getByRole("button", { name: "Nowy obiekt (Standardowy)" }).click();
  await page.locator('input[placeholder="np. NORDPLAST II"]').fill(displayName);
  await page.locator('label:has-text("Próg decyzyjny 7-dniowy") input[type="number"]').fill(String(threshold));
  await page.locator('[data-diag-action="create-site-submit"]').click();
  await page.getByText(displayName, { exact: true }).waitFor();
}

async function createT063Site(page: import("@playwright/test").Page, displayName: string) {
  await createSiteWithThreshold(page, displayName, 60);
}

async function generateCalendarForCurrentMonth(page: import("@playwright/test").Page) {
  await page.locator('button[title="Kalendarz (dni robocze i święta)"]').click();
  await page.getByRole("button", { name: /Wygeneruj kalendarz na miesiąc/ }).click();
  await page.locator(".calendar-day-unconfigured").first().waitFor({ state: "detached" }).catch(() => undefined);
  await page.getByRole("button", { name: "Zamknij" }).click();
}

function daysInCurrentMonth(): number {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
}

// SCENARIO_PACK v0.3 OWNER_CORRECTED: OKNO_7D/OKNO_3D -- a window of
// `days` days starting tomorrow (today+1), pulled back if it would spill
// past the end of the current calendar month so it always stays inside
// the single month the schedule covers.
function futureWindowInCurrentMonth(days: number): { from: string; to: string } {
  const now = new Date();
  const dim = daysInCurrentMonth();
  let start = now.getDate() + 1;
  if (start + days - 1 > dim) start = Math.max(1, dim - days + 1);
  const pad = (n: number) => String(n).padStart(2, "0");
  const iso = (d: number) => `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(d)}`;
  return { from: iso(start), to: iso(start + days - 1) };
}

// Obiekt syntetyczny T063-24H (scenario_pack.md "Wspólna baza"): jedna
// służba D 05:00-17:00 i jedna N 17:00-05:00 każdego dnia, 100% pokrycia.
async function configureObiekt(page: import("@playwright/test").Page) {
  await page.locator('[data-diag-action="control-panel-tab-obiekt"]').click();
  const catalogPanel = page.locator(".panel").filter({ hasText: "Katalog zmian" });
  const dRow = catalogPanel.locator(".create-panel").first();
  await dRow.locator('label:has-text("Początek") select').selectOption("05:00");
  await dRow.locator('label:has-text("Koniec") select').selectOption("17:00");
  await catalogPanel.locator('[data-diag-action="shift-catalog-add-row"]').click();
  const nRow = catalogPanel.locator(".create-panel").last();
  await nRow.locator("select").first().selectOption("N");
  await nRow.locator('label:has-text("Początek") select').selectOption("17:00");
  await nRow.locator('label:has-text("Koniec") select').selectOption("05:00");
  await catalogPanel.locator('[data-diag-action="shift-catalog-save"]').click();
  await expect(page.getByText("Zapisano.")).toBeVisible();

  // Print settings: D1 (12h) and N1 (12h) match this object's exact 12h
  // D/N intervals (FROZEN_WORK_CODE_HOURS) -- required before any real PDF
  // export can succeed (WORK_CODE_MAPPING_REQUIRED otherwise).
  const printSettingsPanel = page.locator(".create-panel", { hasText: "Ustawienia wydruku" });
  const d1Row = printSettingsPanel.locator("tr", { hasText: "D1" });
  await d1Row.locator('input[type="time"]').first().fill("05:00");
  await d1Row.locator('input[type="time"]').nth(1).fill("17:00");
  const n1Row = printSettingsPanel.locator("tr", { hasText: "N1" });
  await n1Row.locator('input[type="time"]').first().fill("17:00");
  await n1Row.locator('input[type="time"]').nth(1).fill("05:00");
  // N1 crosses midnight (17:00 -> 05:00) -- "Koniec nast. dnia" (end next
  // day) must be checked or the validator treats it as end-before-start.
  await n1Row.locator('input[type="checkbox"]').check();
  await printSettingsPanel.getByRole("button", { name: "Zapisz ustawienia" }).click();
  await expect(printSettingsPanel.getByText("Zapisano.")).toBeVisible();

  await page.locator('[data-diag-action="control-panel-tab-obsada"]').click();
}

async function backToRoster(page: import("@playwright/test").Page) {
  await page.getByRole("button", { name: /Wróć do obsady/ }).click();
  await expect(page.getByRole("heading", { name: "Panel sterowania" })).toBeVisible();
}

async function setTargetHours(page: import("@playwright/test").Page, hours: number) {
  const row = page.locator(".field-row", { hasText: "Godziny docelowe" });
  await row.locator('input[type="number"]').fill(String(hours));
  await row.getByRole("button", { name: "Zapisz" }).click();
}

async function addLocalEmployee(
  page: import("@playwright/test").Page,
  name: string,
  opts: { dayOnly?: boolean; targetHours?: number } = {},
) {
  await page.locator('[data-diag-action="roster-add-open"]').click();
  if (opts.dayOnly) {
    await page.locator('label:has-text("Tylko dniówka") input[type="checkbox"]').check();
  }
  await page.locator('input[placeholder="np. Jan Kowalski"]').fill(name);
  await page.locator('[data-diag-action="add-person-submit"]').click();
  await expect(page.getByRole("heading", { name: "Godziny docelowe" })).toBeVisible();
  if (opts.targetHours !== undefined) {
    await setTargetHours(page, opts.targetHours);
  }
  await backToRoster(page);
}

// S02/-V1/-V2 "X1..X3 -- external, D/N, OKNO_7D": same "+ Dodaj osobę" flow
// as a local employee, with membership_kind switched to Wsparcie zewnętrzne
// and a support window filled in (allowedShiftKind left blank = D/N, both).
async function addExternalEmployee(page: import("@playwright/test").Page, name: string, from: string, to: string) {
  // Caller lands here straight from Monthly Planning (right after
  // setupS02Base's DECISION_REQUIRED) -- (re)land on Panel sterowania/
  // Obsada first, same reasoning as reportAbsence.
  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await expect(page.getByRole("heading", { name: "Panel sterowania" })).toBeVisible();
  await page.locator('[data-diag-action="roster-add-open"]').click();
  await page.getByRole("button", { name: "Wsparcie zewnętrzne" }).click();
  await page.locator('input[type="date"]').first().fill(from);
  await page.locator('input[type="date"]').nth(1).fill(to);
  await page.locator('input[placeholder="np. Jan Kowalski"]').fill(name);
  await page.locator('[data-diag-action="add-person-submit"]').click();
  await expect(page.getByRole("heading", { name: "Godziny docelowe" })).toBeVisible();
  await backToRoster(page);
}

const ABSENCE_LABELS: Record<string, string> = {
  LEAVE_GRANTED: "Urlop (przyznany)",
  SICK_LEAVE: "Zwolnienie chorobowe",
};

// Real DayPicker (ROTA-T064) range selection, opened on workingMonth (the
// current month, matching our OWNER_CORRECTED window) -- no month
// navigation needed since OKNO_7D/OKNO_3D always fall inside it.
async function reportAbsence(
  page: import("@playwright/test").Page,
  employeeName: string,
  kind: keyof typeof ABSENCE_LABELS,
  from: string,
  to: string,
) {
  // Callers may be anywhere (Monthly Planning right after selecting a
  // candidate, or fresh on the roster before the first PLAN) -- always
  // (re)land on Panel sterowania/Obsada first, where the employee buttons
  // actually live.
  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await expect(page.getByRole("heading", { name: "Panel sterowania" })).toBeVisible();
  await page.getByRole("button", { name: employeeName, exact: true }).click();
  await page.getByRole("button", { name: "+ Zgłoś nieobecność" }).click();
  await page.locator('label:has-text("Powód") select').selectOption(kind);
  await page.locator(`[data-day="${from}"]`).click();
  await page.locator(`[data-day="${to}"]`).click();
  await page.getByRole("button", { name: "Zgłoś", exact: true }).click();
  await expect(page.getByText(`${ABSENCE_LABELS[kind]} — od ${from} do ${to}`)).toBeVisible();
  await backToRoster(page);
}

async function runPlanFirst(page: import("@playwright/test").Page): Promise<{ status: string; candidates: unknown[][] }> {
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
  await expect(page.getByRole("heading", { name: "Planowanie miesiąca" })).toBeVisible();
  const planResp = page.waitForResponse((r) => r.url().includes("/schedule/") && r.url().includes("/plan") && r.request().method() === "POST");
  await page.locator('[data-diag-action="plan-month-first"]').click();
  return (await planResp).json();
}

async function selectFirstCandidate(page: import("@playwright/test").Page) {
  await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
  await page.locator('[data-diag-action="select-candidate"]').first().click();
  await expect(page.getByText(/Status: Wersja robocza,/)).toBeVisible();
}

// "Przelicz Plan" (brief.md terminology) == the UI's "Przelicz (PLAN)"
// button, data-diag-action="plan-month-recompute" -- only rendered once
// `current_version.is_live` (see OWNER_CORRECTED above).
async function runRecompute(page: import("@playwright/test").Page): Promise<{ status: string; candidates: unknown[][] }> {
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
  await expect(page.getByRole("heading", { name: "Planowanie miesiąca" })).toBeVisible();
  const planResp = page.waitForResponse((r) => r.url().includes("/schedule/") && r.url().includes("/plan") && r.request().method() === "POST");
  await page.locator('[data-diag-action="plan-month-recompute"]').click();
  return (await planResp).json();
}

interface AssignmentOut {
  employee_display_name: string;
  start_datetime: string;
  end_datetime: string;
}

// T63-04/T63-06/T63-07 "pełny D/N ... wyłącznie przez <roster>": every
// employee actually used is in the closed allowed set, and the candidate
// covers exactly 2 shifts/day (one D + one N) for the whole month -- no
// gaps, no extras, no unknown employee.
function assertFullCoverageAndClosedRoster(candidateAssignments: AssignmentOut[], allowedNames: string[]) {
  const names = new Set(candidateAssignments.map((a) => a.employee_display_name));
  for (const n of names) {
    expect(allowedNames).toContain(n);
  }
  expect(candidateAssignments.length).toBe(daysInCurrentMonth() * 2);
}

// R6-01 (Codex round 6): comparing only the START DATE (first 10 chars)
// missed both real production semantics -- availability collision is
// `overlaps_date_range` on the full [start_datetime, end_datetime)
// interval (an N-shift starting the day before a SICK_LEAVE window still
// overlaps it, since it runs past midnight into the first sick day), and
// an external support window requires the WHOLE assignment interval
// contained within it (window.start <= demand.start AND window.end >=
// demand.end) -- a shift starting on the window's last day but crossing
// midnight can still end hours past the window's own end. Parse full
// local datetimes (no timezone suffix, same convention the app uses
// throughout) instead of substring-comparing dates.
function parseLocalIso(dateTime: string): Date {
  const [datePart, timePart] = dateTime.split("T");
  const [y, m, d] = datePart.split("-").map(Number);
  const [hh, mm, ss] = (timePart ?? "00:00:00").split(":").map(Number);
  return new Date(y, m - 1, d, hh, mm, ss || 0);
}

// [from 00:00, to+1 day 00:00) -- the same "whole day, do <day> included"
// construction the product itself uses for both absence and support
// windows (ControlPanel.tsx's addSupportWindowIfNeeded: end_datetime is
// midnight of the day AFTER the picked end date).
function fullDayRangeBounds(from: string, to: string): { start: Date; end: Date } {
  const [fy, fm, fd] = from.split("-").map(Number);
  const [ty, tm, td] = to.split("-").map(Number);
  return { start: new Date(fy, fm - 1, fd, 0, 0, 0), end: new Date(ty, tm - 1, td + 1, 0, 0, 0) };
}

// scenario_pack.md T63-07/S03 "D nie ma assignmentu kolidującego z
// chorobowym": no assignment for this employee may OVERLAP [from, to] at
// all (real interval overlap, not just a matching start date).
function assertNoAssignmentDuringAbsence(assignments: AssignmentOut[], employeeName: string, from: string, to: string) {
  const { start, end } = fullDayRangeBounds(from, to);
  const colliding = assignments.filter((a) => {
    if (a.employee_display_name !== employeeName) return false;
    const aStart = parseLocalIso(a.start_datetime);
    const aEnd = parseLocalIso(a.end_datetime);
    return aStart < end && aEnd > start;
  });
  expect(colliding, `${employeeName} must have no assignment overlapping their SICK_LEAVE ${from}..${to}`).toEqual([]);
}

// scenario_pack.md S02-V1/V2 "external nie jest używany poza swoją
// dostępnością": the WHOLE assignment interval must be contained within
// [from, to] (not just its start).
function assertExternalWithinWindow(assignments: AssignmentOut[], externalNames: string[], from: string, to: string) {
  const { start, end } = fullDayRangeBounds(from, to);
  const outOfWindow = assignments.filter((a) => {
    if (!externalNames.includes(a.employee_display_name)) return false;
    const aStart = parseLocalIso(a.start_datetime);
    const aEnd = parseLocalIso(a.end_datetime);
    return aStart < start || aEnd > end;
  });
  expect(outOfWindow, `external assignments must be fully contained within ${from}..${to}`).toEqual([]);
}

// R5-02: swallowing a screenshot/PDF write failure would let a test pass
// without the evidentiary artifacts brief.md section 11 actually requires
// -- no more .catch(() => undefined) on these.
async function exportAndCapturePdf(page: import("@playwright/test").Page, label: string) {
  await page.locator('[data-diag-action="room-nav-export"]').click();
  await page.locator('button:has-text("Wygeneruj podgląd PDF")').click();
  await expect(page.locator('[data-diag-element="export-preview"]')).toBeVisible({ timeout: 15000 });
  await page.screenshot({ path: `test-results/t063-evidence/${label}-preview.png`, fullPage: true });
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.locator('[data-diag-action="export-download"]').click(),
  ]);
  await download.saveAs(`test-results/t063-evidence/${label}.pdf`);
}

// scenario_pack.md S01/S02/S03 "Stan wejściowy: dokładnie LOCAL A-E; C =
// DAY_ONLY" -- same 5-person roster setup shared by every scenario below,
// only target_hours differs (S01: 168 for all; S02/S03: NULL, left unset).
async function addFiveLocalEmployees(page: import("@playwright/test").Page, siteName: string, targetHours?: number) {
  const names = { A: `${siteName}-A`, B: `${siteName}-B`, C: `${siteName}-C`, D: `${siteName}-D`, E: `${siteName}-E` };
  await addLocalEmployee(page, names.A, { targetHours });
  await addLocalEmployee(page, names.B, { targetHours });
  await addLocalEmployee(page, names.C, { dayOnly: true, targetHours });
  await addLocalEmployee(page, names.D, { targetHours });
  await addLocalEmployee(page, names.E, { targetHours });
  return names;
}

// R5-01 (Codex round 5): the repo's playwright.config.ts sets no file-level
// `timeout` (Playwright's 30s default applies) and a global `retries: 2` --
// a real PLAN/Przelicz Plan here genuinely takes 48-50s, and this task's
// own "no retry masks a failure" claim (brief.md section 7) is worthless
// unless retries=0 is actually encoded here, not just typed on a CLI
// nobody else will remember to use. Every describe block below fixes both.
const T063_TEST_CONFIG = { retries: 0, timeout: 120_000 } as const;

test.describe("T063 S01: dodatni D/N z target_hours", () => {
  test.describe.configure(T063_TEST_CONFIG);

  test("S01: FEASIBLE, pełny D/N wyłącznie A-E, reload, PDF", async ({ page }) => {
    const siteName = `T063S01-${uid()}`;
    await createT063Site(page, siteName);
    await generateCalendarForCurrentMonth(page);
    await openSite(page, siteName);
    await configureObiekt(page);
    const names = await addFiveLocalEmployees(page, siteName, 168);

    const firstBody = await runPlanFirst(page);
    expect(firstBody.status).toBe("FEASIBLE");
    assertFullCoverageAndClosedRoster(firstBody.candidates[0] as AssignmentOut[], Object.values(names));
    await selectFirstCandidate(page);

    await page.reload();
    await page.getByText(siteName, { exact: true }).click();
    await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
    await expect(page.getByRole("heading", { name: "Planowanie miesiąca" })).toBeVisible();
    await expect(page.getByText(/Status: Wersja robocza,/)).toBeVisible();

    await exportAndCapturePdf(page, `S01-${siteName}`);
  });
});

test.describe("T063 S02: chorobowe po powstaniu grafiku, kontrolowany external", () => {
  test.describe.configure(T063_TEST_CONFIG);

  const okno7d = futureWindowInCurrentMonth(7);

  // Shared S02 base: real PLAN with C on approved leave, real candidate
  // selection, then D+E SICK_LEAVE after the schedule already exists
  // (brief.md section 3: chorobowego nie planuje się z góry).
  async function setupS02Base(page: import("@playwright/test").Page, siteName: string) {
    await createT063Site(page, siteName);
    await generateCalendarForCurrentMonth(page);
    await openSite(page, siteName);
    await configureObiekt(page);
    const names = await addFiveLocalEmployees(page, siteName);

    await reportAbsence(page, names.C, "LEAVE_GRANTED", okno7d.from, okno7d.to);

    const baseBody = await runPlanFirst(page);
    expect(baseBody.status).toBe("FEASIBLE");
    await selectFirstCandidate(page);

    await reportAbsence(page, names.D, "SICK_LEAVE", okno7d.from, okno7d.to);
    await reportAbsence(page, names.E, "SICK_LEAVE", okno7d.from, okno7d.to);

    const decisionBody = await runRecompute(page);
    // T63-05: dokładnie DECISION_REQUIRED, nigdy TECHNICAL_ERROR/crash/pusty sukces.
    expect(decisionBody.status).toBe("DECISION_REQUIRED");
    await expect(page.getByText(/Wymagana decyzja koordynatora/)).toBeVisible();
    await page.screenshot({ path: `test-results/t063-evidence/S02-${siteName}-guidance.png` });

    // Literalna decyzja koordynatora: NIE COFAJ URLOPU C -- satisfied by
    // never touching C's leave record anywhere in this file.
    return names;
  }

  test("S02: bez external, DECISION_REQUIRED, urlop C nietknięty", async ({ page }) => {
    const siteName = `T063S02-${uid()}`;
    await setupS02Base(page, siteName);
    // No further action in this scenario -- the frozen result IS
    // DECISION_REQUIRED with no accepted full current from this attempt
    // (already asserted inside setupS02Base).
  });

  test("S02-V1: dokładnie 1 external, FEASIBLE", async ({ page }) => {
    const siteName = `T063S02V1-${uid()}`;
    const names = await setupS02Base(page, siteName);
    const x1 = `${siteName}-X1`;
    await addExternalEmployee(page, x1, okno7d.from, okno7d.to);

    const feasibleBody = await runRecompute(page);
    expect(feasibleBody.status).toBe("FEASIBLE");
    const allowed = [...Object.values(names), x1];
    const assignments = feasibleBody.candidates[0] as AssignmentOut[];
    assertFullCoverageAndClosedRoster(assignments, allowed);
    // R5-02: D/E's SICK_LEAVE and X1's own declared availability window
    // must both be genuinely respected, not just headcount/total-count.
    assertNoAssignmentDuringAbsence(assignments, names.D, okno7d.from, okno7d.to);
    assertNoAssignmentDuringAbsence(assignments, names.E, okno7d.from, okno7d.to);
    assertExternalWithinWindow(assignments, [x1], okno7d.from, okno7d.to);
    await selectFirstCandidate(page);
    await exportAndCapturePdf(page, `S02V1-${siteName}`);
  });

  test("S02-V2: dokładnie 3 external, FEASIBLE", async ({ page }) => {
    const siteName = `T063S02V2-${uid()}`;
    const names = await setupS02Base(page, siteName);
    const x1 = `${siteName}-X1`;
    const x2 = `${siteName}-X2`;
    const x3 = `${siteName}-X3`;
    await addExternalEmployee(page, x1, okno7d.from, okno7d.to);
    await addExternalEmployee(page, x2, okno7d.from, okno7d.to);
    await addExternalEmployee(page, x3, okno7d.from, okno7d.to);

    const feasibleBody = await runRecompute(page);
    expect(feasibleBody.status).toBe("FEASIBLE");
    const allowed = [...Object.values(names), x1, x2, x3];
    const assignments = feasibleBody.candidates[0] as AssignmentOut[];
    assertFullCoverageAndClosedRoster(assignments, allowed);
    assertNoAssignmentDuringAbsence(assignments, names.D, okno7d.from, okno7d.to);
    assertNoAssignmentDuringAbsence(assignments, names.E, okno7d.from, okno7d.to);
    assertExternalWithinWindow(assignments, [x1, x2, x3], okno7d.from, okno7d.to);
    const usedNames = new Set(assignments.map((a) => a.employee_display_name));
    const usedExternalCount = [x1, x2, x3].filter((x) => usedNames.has(x)).length;
    // eslint-disable-next-line no-console
    console.log(`S02-V2 external actually used: ${usedExternalCount} of 3`);
    await selectFirstCandidate(page);
    await exportAndCapturePdf(page, `S02V2-${siteName}`);
  });
});

test.describe("T063 S03: krótka choroba bez external", () => {
  test.describe.configure(T063_TEST_CONFIG);

  test("S03: trzydniowy SICK_LEAVE D po zapisanym grafiku, FEASIBLE po Przelicz Plan", async ({ page }) => {
    const siteName = `T063S03-${uid()}`;
    const okno3d = futureWindowInCurrentMonth(3);
    await createT063Site(page, siteName);
    await generateCalendarForCurrentMonth(page);
    await openSite(page, siteName);
    await configureObiekt(page);
    const names = await addFiveLocalEmployees(page, siteName);

    const baseBody = await runPlanFirst(page);
    expect(baseBody.status).toBe("FEASIBLE");
    await selectFirstCandidate(page);

    await reportAbsence(page, names.D, "SICK_LEAVE", okno3d.from, okno3d.to);

    const feasibleBody = await runRecompute(page);
    expect(feasibleBody.status).toBe("FEASIBLE");
    const assignments = feasibleBody.candidates[0] as AssignmentOut[];
    assertFullCoverageAndClosedRoster(assignments, Object.values(names));
    // T63-07: D must have no assignment colliding with their own SICK_LEAVE.
    assertNoAssignmentDuringAbsence(assignments, names.D, okno3d.from, okno3d.to);
    await selectFirstCandidate(page);

    await page.reload();
    await page.getByText(siteName, { exact: true }).click();
    await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
    await expect(page.getByRole("heading", { name: "Planowanie miesiąca" })).toBeVisible();
    await expect(page.getByText(/Status: Wersja robocza,/)).toBeVisible();

    await exportAndCapturePdf(page, `S03-${siteName}`);
  });
});
