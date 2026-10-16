// ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID (brief.md section 3 point 4): the
// coverage the existing specs do not already give for the moved
// ScheduleGrid -- all three real usages (current schedule, persisted
// candidate preview, old-version history preview), NN (T037), S1 (T052),
// ORDINARY hour labels (T065) and the click into a person/day correction.
// delegation-schedule-grid.spec.ts keeps owning the DEL-only row cases.
//
// Test data only, through the existing API (same endpoints the UI calls).
// Every expected cell/total is derived from the very payload the screen
// renders (month view / plan preview / version snapshot), using the
// frozen display contract -- not from the component's own code:
//   operational_code (NN) wins; PERIODIC_TRAINING -> "S1"; role-bearing
//   demand -> "<start hour>–<end hour>"; otherwise the demand's D/N; several
//   items in one cell joined by "/"; DEL only in a cell with no Assignment;
//   row total = PRIMARY non-CANCELLED hours + DELEGACJA hours, "<n>h".
// Uses the real current month (a live schedule is needed for history
// previews), so NN needs an already-started shift and S1 a not-yet-started
// last day: not runnable on the 1st or the last day of a month.
import { expect, test, type APIRequestContext, type Locator, type Page } from "@playwright/test";

test.use({ timezoneId: "Europe/Warsaw" });
test.describe.configure({ retries: 0, timeout: 180_000 });

type Json = Record<string, any>;

const pad = (n: number) => String(n).padStart(2, "0");
const now = new Date();
const YM = `${now.getFullYear()}-${pad(now.getMonth() + 1)}`;
const M1 = `${YM}-01`;
const LAST_DAY = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
const day = (d: number) => `${YM}-${pad(d)}`;
const uid = () => Math.random().toString(36).slice(2, 8);

async function ok(resp: Awaited<ReturnType<APIRequestContext["get"]>>): Promise<Json | null> {
  if (!resp.ok()) throw new Error(`${resp.url()} -> ${resp.status()} ${await resp.text()}`);
  const text = await resp.text();
  return text ? JSON.parse(text) : null;
}

const strip = (a: Json) => {
  const { employee_display_name: _drop, ...rest } = a;
  return rest;
};

async function createSite(rq: APIRequestContext, name: string, regime: "OCHRONA" | "ORDINARY"): Promise<string> {
  const r = await ok(await rq.post("/api/workspace/sites", {
    data: { display_name: name, rolling_7d_decision_threshold_hours: 60, planning_regime: regime },
  }));
  await ok(await rq.post("/api/workspace/calendar/generate", { data: { month: M1, site_id: r!.site_id } }));
  return r!.site_id as string;
}

async function addEmployee(rq: APIRequestContext, siteId: string, name: string, target: number, positionRoleId?: string) {
  const id = crypto.randomUUID();
  await ok(await rq.post("/api/workspace/employees", { data: { employee_id: id, site_id: siteId, display_name: name, day_only: false } }));
  await ok(await rq.post(`/api/workspace/sites/${siteId}/roster`, { data: { employee_id: id, position_role_id: positionRoleId ?? null } }));
  await ok(await rq.post(`/api/workspace/employees/${id}/target-hours`, { data: { site_id: siteId, month: M1, target_hours: target } }));
  return id;
}

async function plan(rq: APIRequestContext, siteId: string, effectiveFrom: string | null): Promise<Json> {
  const r = await ok(await rq.post(`/api/workspace/sites/${siteId}/schedule/${M1}/plan`, {
    data: { effective_from: effectiveFrom, search_attempt: 0 }, timeout: 120_000,
  }));
  expect(r!.status, String(r!.error_message)).toBe("FEASIBLE");
  return r!;
}

async function planAndAccept(rq: APIRequestContext, siteId: string) {
  const r = await plan(rq, siteId, M1);
  await ok(await rq.post(`/api/workspace/sites/${siteId}/schedule/${M1}/select-candidate`, {
    data: { candidate: r.candidates[0].map(strip), note: null },
  }));
}

const monthView = async (rq: APIRequestContext, siteId: string) => (await ok(await rq.get(`/api/workspace/sites/${siteId}/schedule/${M1}`)))!;

// S1 on the month's last day, for someone free that day and the day before.
async function addS1OnLastDay(rq: APIRequestContext, siteId: string, employees: Record<string, string>): Promise<string> {
  const v = await monthView(rq, siteId);
  const busy = new Set(
    v.assignments.filter((a: Json) => [day(LAST_DAY - 1), day(LAST_DAY)].includes(a.start_datetime.slice(0, 10))).map((a: Json) => a.employee_id),
  );
  const name = Object.keys(employees).find((n) => !busy.has(employees[n]))!;
  await ok(await rq.post(`/api/workspace/sites/${siteId}/schedule/${M1}/manual-correction`, {
    data: {
      upsert_assignments: [{
        assignment_id: crypto.randomUUID(), schedule_version_id: v.current_version.version_id, employee_id: employees[name],
        start_datetime: `${day(LAST_DAY)}T08:00:00`, end_datetime: `${day(LAST_DAY)}T16:00:00`, role: "PERIODIC_TRAINING",
        state: "PLANNED", frozen: false, covers_demand_id: null, mentor_primary_assignment_id: null, operational_code: null,
        work_period_id: null, required_rest_after_hours: null, manual_work_role_id: null, manual_work_role_name: null,
      }],
      note: null,
    },
  }));
  return name;
}

// OCHRONA: D 05-17 + N 17-05 daily, five LOCAL people, Ewa on DELEGACJA 27-28.
async function seedOchronaAccepted(rq: APIRequestContext, name: string) {
  const siteId = await createSite(rq, name, "OCHRONA");
  await ok(await rq.put(`/api/workspace/sites/${siteId}/shift-catalog`, { data: { shifts: [
    { kind: "D", start_time: "05:00", end_time: "17:00", required_primary_count: 1, active_weekdays: [1, 2, 3, 4, 5, 6, 7] },
    { kind: "N", start_time: "17:00", end_time: "05:00", required_primary_count: 1, active_weekdays: [1, 2, 3, 4, 5, 6, 7] },
  ] } }));
  await ok(await rq.put(`/api/workspace/sites/${siteId}/delegation-default-hours`, { data: { delegation_default_hours: 8 } }));
  const employees: Record<string, string> = {};
  for (const n of ["Anna", "Bartek", "Celina", "Darek", "Ewa"]) employees[n] = await addEmployee(rq, siteId, n, 150);
  await ok(await rq.post(`/api/workspace/employees/${employees.Ewa}/availability`, { data: {
    site_id: siteId, availability_id: crypto.randomUUID(), kind: "DELEGACJA", start_date: day(27), end_date: day(28), delegation_hours: 8,
  } }));
  await planAndAccept(rq, siteId);
  return { siteId, employees };
}

async function openPlanning(page: Page, siteName: string) {
  await page.goto("/");
  await page.getByText(siteName, { exact: true }).click();
  await page.locator('[data-diag-action="room-nav-monthly-planning"]').click();
  await expect(page.getByRole("heading", { name: "Planowanie miesiąca" })).toBeVisible();
  await expect(page.locator("table.grid-table").first()).toBeVisible();
}

interface GridSource {
  assignments: Json[];
  demands: Json[];
  employees?: { employee_id: string; employee_display_name: string }[];
  delegation_days?: { employee_id: string; date: string; code: string; hours: number }[];
}

// Computed in the browser page (same timezone as the rendered grid), from
// the payload alone -- see the contract summary at the top of this file.
async function expectedGrid(page: Page, src: GridSource) {
  return page.evaluate((s: GridSource) => {
    const demandById = new Map(s.demands.map((d) => [d.demand_id, d]));
    const [y, m] = s.assignments.length ? s.assignments[0].start_datetime.slice(0, 7).split("-").map(Number) : [0, 0];
    const ym = s.assignments[0].start_datetime.slice(0, 7);
    const n = new Date(y, m, 0).getDate();
    const days = Array.from({ length: n }, (_, i) => `${ym}-${String(i + 1).padStart(2, "0")}`);
    const people = s.employees
      ? s.employees.map((e) => [e.employee_id, e.employee_display_name])
      : Array.from(new Map(s.assignments.map((a) => [a.employee_id, a.employee_display_name])).entries());
    const label = (a: Json) => {
      if (a.operational_code) return a.operational_code;
      if (a.role === "PERIODIC_TRAINING") return "S1";
      const d = a.covers_demand_id ? demandById.get(a.covers_demand_id) : undefined;
      const base = d?.required_role
        ? `${new Date(a.start_datetime).getHours()}–${new Date(a.end_datetime).getHours()}`
        : (d?.shift_kind ?? "?");
      return a.role === "TRAINEE" ? `${base}·S` : base;
    };
    const hours = (a: Json) => Math.round((new Date(a.end_datetime).getTime() - new Date(a.start_datetime).getTime()) / 3600000);
    const rows: Record<string, { cells: string[]; total: string }> = {};
    for (const [id, name] of people) {
      const mine = s.assignments.filter((a) => a.employee_id === id);
      const del = (s.delegation_days ?? []).filter((d) => d.employee_id === id);
      const cells = days.map((dd) => {
        const items = mine.filter((a) => a.start_datetime.slice(0, 10) === dd);
        if (items.length) return items.map(label).join("/");
        return del.find((d) => d.date === dd)?.code ?? "";
      });
      const total = mine.filter((a) => a.role === "PRIMARY" && a.state !== "CANCELLED").reduce((t, a) => t + hours(a), 0)
        + del.reduce((t, d) => t + d.hours, 0);
      rows[name] = { cells, total: `${total}h` };
    }
    return { header: ["Pracownik", ...days.map((d) => d.slice(8, 10)), "Suma godzin"], rows };
  }, src);
}

async function renderedGrid(table: Locator) {
  return table.evaluate((t) => ({
    header: Array.from(t.querySelectorAll("thead th")).map((th) => th.textContent ?? ""),
    rows: Array.from(t.querySelectorAll("tbody tr")).map((tr) => Array.from(tr.querySelectorAll("td")).map((td) => (td.textContent ?? "").replace("🔒", ""))),
    buttons: t.querySelectorAll("button").length,
  }));
}

async function expectGridMatches(table: Locator, page: Page, src: GridSource, opts: { clickable: boolean }) {
  const want = await expectedGrid(page, src);
  const got = await renderedGrid(table);
  expect(got.header).toEqual(want.header);
  expect(got.rows.map((r) => r[0]).sort()).toEqual(Object.keys(want.rows).sort());
  for (const row of got.rows) {
    const w = want.rows[row[0]];
    expect(row.slice(1, -1), `cells of ${row[0]}`).toEqual(w.cells);
    expect(row[row.length - 1], `total of ${row[0]}`).toBe(w.total);
  }
  if (opts.clickable) expect(got.buttons).toBeGreaterThan(0);
  else expect(got.buttons).toBe(0);
  return got;
}

function trackWrites(page: Page): string[] {
  const writes: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/") && r.method() !== "GET") writes.push(`${r.method()} ${new URL(r.url()).pathname}`);
  });
  return writes;
}

test("current grid shows NN/S1/DEL from the month view, click opens that person/day correction, history preview shows the old version read-only", async ({ page, request }) => {
  const siteName = `RG-HIST-${uid()}`;
  const { siteId, employees } = await seedOchronaAccepted(request, siteName);
  const v1 = await monthView(request, siteId);
  const started = v1.assignments
    .filter((a: Json) => a.employee_id === employees.Anna && a.start_datetime < `${day(now.getDate())}T00:00:00`)
    .sort((a: Json, b: Json) => a.start_datetime.localeCompare(b.start_datetime))[0];
  await ok(await request.post(`/api/workspace/sites/${siteId}/schedule/${M1}/manual-correction/mark-not-worked`, {
    data: { assignment_id: started.assignment_id },
  }));
  const s1Name = await addS1OnLastDay(request, siteId, employees);
  const view = await monthView(request, siteId);

  const writes = trackWrites(page);
  await openPlanning(page, siteName);
  const current = page.locator("table.grid-table").first();
  const got = await expectGridMatches(current, page, view, { clickable: true });
  // The three special cells this Task must keep, named explicitly.
  const nnDay = Number(started.start_datetime.slice(8, 10));
  expect(got.rows.find((r) => r[0] === "Anna")![nnDay]).toBe("NN");
  expect(got.rows.find((r) => r[0] === s1Name)![LAST_DAY]).toBe("S1");
  const ewa = got.rows.find((r) => r[0] === "Ewa")!;
  expect([ewa[27], ewa[28]]).toEqual(["DEL", "DEL"]);

  // Click -> the correction panel for exactly that person and day.
  const bartek = page.getByRole("row", { name: /Bartek/ });
  const button = bartek.locator('[data-diag-action="manual-correction-select-assignment"]').first();
  const column = await button.evaluate((b) => Array.from(b.closest("tr")!.children).indexOf(b.closest("td")!));
  await button.click();
  await expect(page.getByRole("heading", { name: `Ręczna korekta — Bartek, ${day(column)}` })).toBeVisible();

  // History: every older version opens read-only and matches its own snapshot.
  await page.locator('[data-diag-action="history-toggle"]').click();
  const previews = page.locator('[data-diag-action="preview-version"]');
  await expect(previews).toHaveCount(2);
  let sawOriginalPlanOnNnDay = false;
  for (let i = 0; i < 2; i++) {
    const snapResp = page.waitForResponse((r) => r.url().includes("/versions/") && r.request().method() === "GET");
    await previews.nth(i).click();
    const snapshot = await (await snapResp).json();
    const panel = page.locator(".panel", { has: page.getByRole("heading", { name: "Podgląd starej wersji" }) }).last();
    await expect(panel.locator("table.grid-table")).toBeVisible();
    const old = await expectGridMatches(panel.locator("table.grid-table"), page, snapshot, { clickable: false });
    if (["D", "N"].includes(old.rows.find((r) => r[0] === "Anna")![nnDay])) sawOriginalPlanOnNnDay = true;
  }
  expect(sawOriginalPlanOnNnDay).toBe(true);
  expect(writes).toEqual([]);
});

test("persisted Przelicz preview: candidate grid carries the fixed S1 and DEL, survives reload, no write on render", async ({ page, request }) => {
  const siteName = `RG-PREV-${uid()}`;
  const { siteId, employees } = await seedOchronaAccepted(request, siteName);
  const s1Name = await addS1OnLastDay(request, siteId, employees);
  await plan(request, siteId, null);
  const view = await monthView(request, siteId);
  expect(view.plan_preview).not.toBeNull();

  const writes = trackWrites(page);
  for (const pass of ["first open", "after reload"]) {
    if (pass === "after reload") await page.reload();
    await openPlanning(page, siteName);
    await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
    const candidate = page.locator(".panel", { has: page.getByRole("heading", { name: "Kandydaci" }) }).last().locator("table.grid-table").first();
    const got = await expectGridMatches(candidate, page, {
      assignments: view.plan_preview.candidates[0], demands: view.demands,
      employees: view.plan_preview.employees, delegation_days: view.plan_preview.delegation_days,
    }, { clickable: false });
    expect(got.rows.find((r) => r[0] === s1Name)![LAST_DAY]).toBe("S1");
    const ewa = got.rows.find((r) => r[0] === "Ewa")!;
    expect([ewa[27], ewa[28]]).toEqual(["DEL", "DEL"]);
    await expectGridMatches(page.locator("table.grid-table").first(), page, view, { clickable: true });
  }
  expect(writes).toEqual([]);
});

test("ORDINARY: current grid and candidate preview show real hours, never D/N", async ({ page, request }) => {
  const siteName = `RG-ORD-${uid()}`;
  const siteId = await createSite(request, siteName, "ORDINARY");
  const roleId = `ROLE-${uid()}`; // role ids are database-wide, not per Site
  await ok(await request.put(`/api/workspace/sites/${siteId}/roles/${roleId}`, { data: { role_id: roleId, display_name: "Sprzedawca" } }));
  await ok(await request.put(`/api/workspace/sites/${siteId}/shift-catalog`, { data: { shifts: [
    { kind: null, start_time: "08:00", end_time: "16:00", required_primary_count: 1, active_weekdays: [1, 2, 3, 4, 5, 6], required_role_id: roleId },
    { kind: null, start_time: "12:00", end_time: "20:00", required_primary_count: 1, active_weekdays: [1, 2, 3, 4, 5, 6], required_role_id: roleId },
  ] } }));
  for (const n of ["Ola", "Piotr", "Rysiek", "Zosia"]) await addEmployee(request, siteId, n, 120, roleId);
  await planAndAccept(request, siteId);
  await plan(request, siteId, null);
  const view = await monthView(request, siteId);

  await openPlanning(page, siteName);
  await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
  const current = await expectGridMatches(page.locator("table.grid-table").first(), page, view, { clickable: true });
  const candidate = await expectGridMatches(
    page.locator(".panel", { has: page.getByRole("heading", { name: "Kandydaci" }) }).last().locator("table.grid-table").first(), page,
    { assignments: view.plan_preview.candidates[0], demands: view.demands, employees: view.plan_preview.employees, delegation_days: view.plan_preview.delegation_days },
    { clickable: false },
  );
  for (const grid of [current, candidate]) {
    const cells = grid.rows.flatMap((r) => r.slice(1, -1)).filter(Boolean);
    expect(cells.length).toBeGreaterThan(0);
    for (const c of cells) expect(c).toMatch(/^(8–16|12–20)(\/(8–16|12–20))*$/);
  }
});
