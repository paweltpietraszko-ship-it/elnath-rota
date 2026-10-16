// ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID evidence harness (round_01 only,
// not a product test). Two phases, same e2e database in between:
//   CAPTURE_PHASE=seed                -> seeds three test-only sites via the
//                                        existing API, writes fixture.json
//   CAPTURE_PHASE=capture CAPTURE_LABEL=base|after
//                                     -> opens every ScheduleGrid usage on
//                                        those exact sites, dumps the grid
//                                        DOM (header, cells, buttons) + a
//                                        screenshot, and logs every non-GET
//                                        /api request fired while doing so.
// compare.py then diffs base vs after.
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const HERE = __dirname;
const FIXTURE = path.join(HERE, "fixture.json");
const PHASE = process.env.CAPTURE_PHASE ?? "capture";
const LABEL = process.env.CAPTURE_LABEL ?? "base";
const OUT = path.join(HERE, LABEL);

test.use({ timezoneId: "Europe/Warsaw", locale: "pl-PL", viewport: { width: 1800, height: 1000 } });

const pad = (n: number) => String(n).padStart(2, "0");
const now = new Date();
const YM = `${now.getFullYear()}-${pad(now.getMonth() + 1)}`;
const M1 = `${YM}-01`;
const LAST_DAY = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
const day = (d: number) => `${YM}-${pad(d)}`;
const uid = () => Math.random().toString(36).slice(2, 8);

type Json = Record<string, any>;

async function ok(resp: Awaited<ReturnType<APIRequestContext["get"]>>): Promise<Json | null> {
  if (!resp.ok()) throw new Error(`${resp.url()} -> ${resp.status()} ${await resp.text()}`);
  const text = await resp.text();
  return text ? JSON.parse(text) : null;
}

const strip = (a: Json) => {
  const { employee_display_name: _d, ...rest } = a;
  return rest;
};

async function createSite(rq: APIRequestContext, name: string, regime: "OCHRONA" | "ORDINARY"): Promise<string> {
  const r = await ok(await rq.post("/api/workspace/sites", {
    data: { display_name: name, rolling_7d_decision_threshold_hours: 60, planning_regime: regime },
  }));
  const siteId = r!.site_id as string;
  await ok(await rq.post("/api/workspace/calendar/generate", { data: { month: M1, site_id: siteId } }));
  return siteId;
}

async function addEmployee(rq: APIRequestContext, siteId: string, name: string, target: number, positionRoleId?: string) {
  const id = crypto.randomUUID();
  await ok(await rq.post("/api/workspace/employees", { data: { employee_id: id, site_id: siteId, display_name: name, day_only: false } }));
  await ok(await rq.post(`/api/workspace/sites/${siteId}/roster`, { data: { employee_id: id, position_role_id: positionRoleId ?? null } }));
  await ok(await rq.post(`/api/workspace/employees/${id}/target-hours`, { data: { site_id: siteId, month: M1, target_hours: target } }));
  return id;
}

async function planAndAccept(rq: APIRequestContext, siteId: string) {
  const r = await ok(await rq.post(`/api/workspace/sites/${siteId}/schedule/${M1}/plan`, { data: { effective_from: M1, search_attempt: 0 }, timeout: 120_000 }));
  if (r!.status !== "FEASIBLE") throw new Error(`PLAN ${r!.status}: ${r!.error_message}`);
  await ok(await rq.post(`/api/workspace/sites/${siteId}/schedule/${M1}/select-candidate`, { data: { candidate: r!.candidates[0].map(strip), note: null } }));
}

async function recompute(rq: APIRequestContext, siteId: string) {
  const r = await ok(await rq.post(`/api/workspace/sites/${siteId}/schedule/${M1}/plan`, { data: { effective_from: null, search_attempt: 0 }, timeout: 120_000 }));
  if (r!.status !== "FEASIBLE") throw new Error(`Przelicz ${r!.status}: ${r!.error_message}`);
}

const monthView = async (rq: APIRequestContext, siteId: string) => (await ok(await rq.get(`/api/workspace/sites/${siteId}/schedule/${M1}`)))!;

async function addS1(rq: APIRequestContext, siteId: string, employees: Record<string, string>, onDay: number) {
  const v = await monthView(rq, siteId);
  const busy = new Set(v.assignments.filter((a: Json) => [day(onDay - 1), day(onDay)].includes(a.start_datetime.slice(0, 10))).map((a: Json) => a.employee_id));
  const name = Object.keys(employees).find((n) => !busy.has(employees[n]))!;
  await ok(await rq.post(`/api/workspace/sites/${siteId}/schedule/${M1}/manual-correction`, {
    data: {
      upsert_assignments: [{
        assignment_id: crypto.randomUUID(), schedule_version_id: v.current_version.version_id, employee_id: employees[name],
        start_datetime: `${day(onDay)}T08:00:00`, end_datetime: `${day(onDay)}T16:00:00`, role: "PERIODIC_TRAINING", state: "PLANNED",
        frozen: false, covers_demand_id: null, mentor_primary_assignment_id: null, operational_code: null,
        work_period_id: null, required_rest_after_hours: null, manual_work_role_id: null, manual_work_role_name: null,
      }],
      note: null,
    },
  }));
  return name;
}

async function seedOchrona(rq: APIRequestContext, name: string) {
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

test("seed", async ({ request }) => {
  test.skip(PHASE !== "seed", "seed phase only");
  // A: current + history -- NN on a past shift, S1 on the last day, DEL days.
  const a = await seedOchrona(request, `RG-HIST-${uid()}`);
  const vA = await monthView(request, a.siteId);
  const past = vA.assignments
    .filter((x: Json) => x.employee_id === a.employees.Anna && x.start_datetime < `${day(now.getDate())}T00:00:00`)
    .sort((x: Json, y: Json) => x.start_datetime.localeCompare(y.start_datetime))[0];
  await ok(await request.post(`/api/workspace/sites/${a.siteId}/schedule/${M1}/manual-correction/mark-not-worked`, { data: { assignment_id: past.assignment_id } }));
  const s1A = await addS1(request, a.siteId, a.employees, LAST_DAY);
  // B: OCHRONA current + Przelicz preview carrying S1 and DEL.
  const b = await seedOchrona(request, `RG-PREV-${uid()}`);
  const s1B = await addS1(request, b.siteId, b.employees, LAST_DAY);
  await recompute(request, b.siteId);
  // C: ORDINARY current + Przelicz preview, hour labels instead of D/N.
  const cName = `RG-ORD-${uid()}`;
  const cId = await createSite(request, cName, "ORDINARY");
  await ok(await request.put(`/api/workspace/sites/${cId}/roles/ROLE-SPRZ`, { data: { role_id: "ROLE-SPRZ", display_name: "Sprzedawca" } }));
  await ok(await request.put(`/api/workspace/sites/${cId}/shift-catalog`, { data: { shifts: [
    { kind: null, start_time: "08:00", end_time: "16:00", required_primary_count: 1, active_weekdays: [1, 2, 3, 4, 5, 6], required_role_id: "ROLE-SPRZ" },
    { kind: null, start_time: "12:00", end_time: "20:00", required_primary_count: 1, active_weekdays: [1, 2, 3, 4, 5, 6], required_role_id: "ROLE-SPRZ" },
  ] } }));
  for (const n of ["Ola", "Piotr", "Rysiek", "Zosia"]) await addEmployee(request, cId, n, 120, "ROLE-SPRZ");
  await planAndAccept(request, cId);
  await recompute(request, cId);
  const sites = await ok(await request.get("/api/workspace/sites"));
  const nameOf = (id: string) => (sites as any[]).find((s) => s.site_id === id).display_name;
  fs.writeFileSync(FIXTURE, JSON.stringify({
    month: YM, seeded_at: new Date().toISOString(),
    A: { ...a, name: nameOf(a.siteId), nn_assignment: past.assignment_id, nn_day: past.start_datetime.slice(0, 10), s1_employee: s1A },
    B: { ...b, name: nameOf(b.siteId), s1_employee: s1B },
    C: { siteId: cId, name: cName },
  }, null, 2));
});

async function dumpGrids(page: Page) {
  return page.evaluate(() => Array.from(document.querySelectorAll("table.grid-table")).map((table) => {
    const panel = table.closest(".panel");
    const prev = table.closest(".matrix-table-wrap")?.previousElementSibling;
    return {
      panel_title: panel?.querySelector("h3")?.textContent ?? null,
      preceding: prev?.textContent ?? null,
      header: Array.from(table.querySelectorAll("thead th")).map((th) => th.textContent),
      rows: Array.from(table.querySelectorAll("tbody tr")).map((tr) => Array.from(tr.querySelectorAll("td")).map((td) => ({
        text: td.textContent,
        style: td.getAttribute("style"),
        buttons: Array.from(td.querySelectorAll("button")).map((b) => ({
          text: b.textContent, title: b.getAttribute("title"), action: b.getAttribute("data-diag-action"), cls: b.className, style: b.getAttribute("style"),
        })),
      }))),
      wrap_class: table.parentElement?.className ?? null,
      table_class: table.className,
    };
  }));
}

async function shot(page: Page, name: string) {
  const grids = page.locator(".matrix-table-wrap");
  const n = await grids.count();
  for (let i = 0; i < n; i++) await grids.nth(i).screenshot({ path: path.join(OUT, `${name}_grid${i}.png`) });
}

async function openPlanning(page: Page, siteName: string, nav = "room-nav-monthly-planning") {
  await page.goto("/");
  await page.getByText(siteName, { exact: true }).click();
  await page.locator(`[data-diag-action="${nav}"]`).click();
  await expect(page.getByRole("heading", { name: "Planowanie miesiąca" })).toBeVisible();
  await expect(page.getByText(/Status: /)).toBeVisible();
  await page.waitForLoadState("networkidle");
}

test("capture", async ({ page }) => {
  test.skip(PHASE !== "capture", "capture phase only");
  const fx = JSON.parse(fs.readFileSync(FIXTURE, "utf-8"));
  fs.mkdirSync(OUT, { recursive: true });
  const writes: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/") && r.method() !== "GET") writes.push(`${r.method()} ${new URL(r.url()).pathname}`);
  });
  const result: Json = { label: LABEL, fixture: fx, steps: {} };
  const step = async (key: string) => {
    result.steps[key] = {
      grids: await dumpGrids(page), writes_so_far: [...writes],
      month_input: await page.locator('[data-diag-element="room-working-month"]').inputValue(),
      content_text_head: (await page.locator(".room-content-inner").innerText()).slice(0, 400),
    };
    await shot(page, key);
  };

  // --- A: current grid, click -> correction, history previews, month switch, korekta/wydruk entries
  await openPlanning(page, fx.A.name);
  await step("A_current");
  const bartekBtn = page.getByRole("row", { name: /Bartek/ }).locator('[data-diag-action="manual-correction-select-assignment"]').first();
  const clickedCell = await bartekBtn.evaluate((b) => {
    const td = b.closest("td")!; return { index: Array.from(td.parentElement!.children).indexOf(td), text: b.textContent };
  });
  await bartekBtn.click();
  const correction = page.getByRole("heading", { name: /^Ręczna korekta — / });
  await expect(correction).toBeVisible();
  result.steps.A_click = { clicked: clickedCell, heading: await correction.textContent(), writes_so_far: [...writes] };
  await page.locator('[data-diag-action="history-toggle"]').click();
  const previews = page.locator('[data-diag-action="preview-version"]');
  const nPreview = await previews.count();
  result.steps.A_history_count = nPreview;
  for (let i = 0; i < nPreview; i++) {
    await previews.nth(i).click();
    await expect(page.getByRole("heading", { name: "Podgląd starej wersji" })).toBeVisible();
    await page.waitForLoadState("networkidle");
    await step(`A_history_${i}`);
  }
  const monthInput = page.locator('[data-diag-element="room-working-month"]');
  const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  await monthInput.fill(`${nextMonth.getFullYear()}-${pad(nextMonth.getMonth() + 1)}`);
  await page.waitForLoadState("networkidle");
  await expect(page.getByText("Ładowanie…")).toHaveCount(0);
  result.steps.A_next_month_text = (await page.locator(".room-content-inner").innerText()).slice(0, 2000);
  await monthInput.fill(fx.month);
  await expect(page.locator("table.grid-table").first()).toBeVisible();
  await page.waitForLoadState("networkidle");
  await step("A_back_to_month");
  await page.locator('[data-diag-action="room-nav-manual-correction"]').click();
  await page.waitForLoadState("networkidle");
  await expect(page.locator("table.grid-table").first()).toBeVisible();
  await step("A_entry_korekta");
  await page.locator('[data-diag-action="room-nav-export"]').click();
  await page.waitForLoadState("networkidle");
  await expect(page.locator("table.grid-table").first()).toBeVisible();
  await step("A_entry_wydruk");

  // --- B: OCHRONA current + persisted Przelicz preview (after a fresh load)
  await openPlanning(page, fx.B.name);
  await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
  await step("B_current_and_preview");
  await page.reload();
  await openPlanning(page, fx.B.name);
  await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
  await step("B_after_reload");

  // --- C: ORDINARY current + preview
  await openPlanning(page, fx.C.name);
  await expect(page.getByRole("heading", { name: "Kandydaci" })).toBeVisible();
  await step("C_current_and_preview");

  result.writes = writes;
  fs.writeFileSync(path.join(OUT, "capture.json"), JSON.stringify(result, null, 2));
});
