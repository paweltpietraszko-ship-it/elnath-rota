// Thin fetch wrapper over api/routers/*. Mirrors the response shapes
// exactly (see api/routers/bootstrap.py, calendar.py, backup.py) --
// no client-side reinterpretation of business fields.

import { recordEvent, newEventId, nowIso, getCurrentScreen } from "../diagnostics/buffer";
import { consumePendingActionId, resolveAction, REQUEST_TIMEOUT_MS } from "../diagnostics/tracking";
import { sanitizeEndpoint } from "../diagnostics/sanitize";
import { getFrontendReport } from "../diagnostics/report";

// ROTA-T032: PLAN/REPLAN can legitimately run up to the solver's own
// operation budget (PLANNING_OPERATION_BUDGET_SECONDS = 45s, see
// rota/planning/solver.py) -- the global REQUEST_TIMEOUT_MS (20s) is too
// short for these two calls specifically and must never abort them
// mid-solve. 45s backend budget + 15s transport/serialization margin;
// every other endpoint keeps the global 20s default.
const PLANNING_REQUEST_TIMEOUT_MS = 60000;

export interface SiteSummary {
  site_id: string;
  display_name: string;
  planning_regime: "OCHRONA" | "ORDINARY";
  complete: boolean;
  missing: string[];
  decision_required_months: string[];
  print_settings_missing: boolean;
  active: boolean;
}

export interface CreateSiteRequest {
  display_name: string;
  profile_display_name: string;
  rolling_7d_decision_threshold_hours: number;
  planning_regime: "OCHRONA" | "ORDINARY";
}

export interface CreateSiteResponse {
  site_id: string;
  profile_id: string;
}

export interface ShiftRowOut {
  kind: "D" | "N";
  start_time: string;
  end_time: string;
  required_primary_count: number;
  active_weekdays: number[];
  duration_hours: number;
  catalog_kind: "12h" | "24h" | "INNY";
}

export interface ShiftCatalogOut {
  shifts: ShiftRowOut[];
}

export interface ShiftRowIn {
  kind: "D" | "N";
  start_time: string;
  end_time: string;
  required_primary_count: number;
  active_weekdays: number[];
}

export interface CalendarDayOut {
  date: string;
  holiday: boolean;
}

// Planowanie miesiąca (T031)
export interface ScheduleVersionOut {
  version_id: string;
  status: "WORKING" | "WORKING_WITH_DEVIATIONS" | "FINAL_NO_DEVIATIONS" | "FINAL_WITH_DEVIATIONS";
  effective_from: string | null;
  created_at: string;
  created_by: string;
  parent_version_id: string | null;
}

export interface ShiftDemandOut {
  demand_id: string;
  start_datetime: string;
  end_datetime: string;
  required_primary_count: number;
  shift_kind: "D" | "N" | null;
}

export interface AssignmentOut {
  assignment_id: string;
  schedule_version_id: string;
  employee_id: string;
  employee_display_name: string;
  start_datetime: string;
  end_datetime: string;
  role: "PRIMARY" | "TRAINEE";
  state: "PLANNED" | "REALIZED" | "CANCELLED";
  frozen: boolean;
  covers_demand_id: string | null;
  mentor_primary_assignment_id: string | null;
  operational_code: string | null;
  work_period_id: string | null;
  required_rest_after_hours: number | null;
}

export interface DeviationOut {
  deviation_id: string;
  category: string;
  source_reference: string;
  label: string;
  affected_assignment_or_employee: string;
  acknowledged: boolean;
}

export interface MonthViewOut {
  current_version: ScheduleVersionOut | null;
  version_history: ScheduleVersionOut[];
  demands: ShiftDemandOut[];
  assignments: AssignmentOut[];
  deviations: DeviationOut[];
  decision_required: DecisionRequiredPayloadOut | null;
  warnings: string[];
}

export interface DecisionRequiredPayloadOut {
  blocking_shift_demands: { demand_id: string; start_datetime: string; end_datetime: string }[];
  blockers: { employee_id: string; condition: string }[];
  load_blocker: { employee_id: string; window_start: string; window_end: string; hours: number } | null;
  unblocking_options: string[];
}

export interface PlanningResultOut {
  status:
    | "FEASIBLE"
    | "DECISION_REQUIRED"
    | "TECHNICAL_ERROR"
    | "NO_ALTERNATIVE"
    | "NARROW_SEARCH_EXHAUSTED"
    | "SEARCH_INCOMPLETE";
  candidates: AssignmentOut[][];
  decision_payload: DecisionRequiredPayloadOut | null;
  error_message: string | null;
  warnings: string[];
  optimization_complete: boolean;
}

export interface PrecheckOut {
  status: "NO_OBVIOUS_SHORTAGE" | "LIKELY_INSUFFICIENT";
  under_covered_demand_ids: string[];
}

// AssignmentIn (select-candidate payload) -- same fields as AssignmentOut
// minus employee_display_name, which the API joins on read and never
// accepts back (api/routers/schedule.py::AssignmentIn, extra="forbid").
export type AssignmentIn = Omit<AssignmentOut, "employee_display_name">;

export interface RosterRow {
  employee_id: string;
  display_name: string;
  enabled: boolean;
  can_work_24h: boolean;
  readiness_state: string;
}

export interface PickableEmployee {
  employee_id: string;
  display_name: string;
  reason: "new" | "re-add";
}

export interface EmployeeOut {
  employee_id: string;
  display_name: string;
  day_only: boolean;
}

export interface MembershipOut {
  enabled: boolean;
  can_work_24h: boolean;
  readiness_state: string;
  readiness_source: string;
}

export interface AvailabilityRecordOut {
  availability_id: string;
  kind: "DAY_SHIFT_OFF" | "UNAVAILABLE_24H" | "LEAVE_PLAN" | "LEAVE_GRANTED" | "SICK_LEAVE";
  start_date: string;
  end_date: string;
  active: boolean;
}

export interface EmployeeDetailOut {
  employee: EmployeeOut;
  membership: MembershipOut;
  availability: AvailabilityRecordOut[];
}

export interface MatrixCellOut {
  rule_id: string;
  rule_version_id: string;
  cell: "dniowka" | "nocka" | "weekday" | "day_only_exception" | "other";
  weekday: number | null;
  effective_from: string;
  effective_to: string | null;
  applies_from: string | null;
  applies_to: string | null;
}

export interface AnalyticsMonthDataOut {
  month: string;
  target_hours: number;
  effective_target_hours: number;
  planned_hours: number;
  realized_hours: number;
  month_balance: number;
  quarter_balance: number | null;
  unresolved_carryover: number | null;
}

export interface EmployeeAnalyticsRowOut {
  employee_id: string;
  display_name: string;
  status: "AVAILABLE" | "MONTH_AVAILABLE_QUARTER_UNAVAILABLE" | "UNAVAILABLE";
  month_data: AnalyticsMonthDataOut | null;
  quarter_months: AnalyticsMonthDataOut[];
  warnings: string[];
}

export interface CoordinatorAnalyticsViewOut {
  site_id: string;
  month: string;
  quarter_first_month: string;
  hours_scope: "ALL_SITES";
  rows: EmployeeAnalyticsRowOut[];
}

export type CoordinatorActionKind =
  | "CONTEXT_CONFIGURATION_SAVED"
  | "EXTERNAL_SUPPORT_WINDOW_CHANGED"
  | "AVAILABILITY_CHANGED"
  | "EMPLOYEE_DAY_ONLY_CHANGED"
  | "SITE_MEMBERSHIP_CHANGED"
  | "TARGET_HOURS_CHANGED"
  | "CALENDAR_DAY_CHANGED"
  | "SITE_PROFILE_CHANGED"
  | "SITE_ACTIVE_CHANGED"
  | "RULE_DECISION_RECORDED"
  | "SCHEDULE_CANDIDATE_SELECTED"
  | "SCHEDULE_REPLAN_CREATED"
  | "MANUAL_SCHEDULE_CORRECTION"
  | "ASSIGNMENT_FREEZE_CHANGED"
  | "ASSIGNMENT_NOT_WORKED"
  | "TRAINING_REALIZED"
  | "SCHEDULE_FINALIZED"
  | "SCHEDULE_RESTORED";

export interface AffectedEntityOut {
  entity_kind: string;
  entity_id: string;
}

export interface MaterialActionSummaryOut {
  action_id: string;
  action_kind: CoordinatorActionKind;
  origin_site_id: string;
  affected_site_ids: string[];
  coordinator_id: string;
  recorded_at: string;
  effective_from: string | null;
  month: string | null;
  schedule_version_id: string | null;
  affected_entities: AffectedEntityOut[];
  note: string | null;
  responds_to_decision_required_id: string | null;
}

export interface DecisionRequiredReadbackOut {
  decision_required_id: string;
  site_id: string;
  month: string;
  schedule_version_id: string | null;
  requested_by: string;
  recorded_at: string;
  linked_action_ids: string[];
}

export interface MaterialActionDetailOut extends MaterialActionSummaryOut {
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  source_kind: string;
  source_id: string | null;
  responds_to: DecisionRequiredReadbackOut | null;
}

export interface DecisionRequiredOut {
  decision_required_id: string;
  site_id: string;
  month: string;
  schedule_version_id: string | null;
  requested_by: string;
  recorded_at: string;
  blocking_shift_demands: { demand_id: string; start_datetime: string; end_datetime: string }[];
  blockers: { employee_id: string; condition: string }[];
  load_blocker: { employee_id: string; window_start: string; window_end: string; hours: number } | null;
  unblocking_options: string[];
  linked_action_ids: string[];
}

export interface DecisionRecordOut {
  decision_id: string;
  site_id: string;
  rule_id: string;
  chain_seq: number;
  statement: string;
  coordinator_id: string;
  recorded_at: string;
  effective_from: string;
  rule_version_id: string | null;
  rel: "supersedes" | "corrects" | "rejects" | null;
  predecessor_decision_id: string | null;
}

async function req<T>(path: string, init?: RequestInit, timeoutMs: number = REQUEST_TIMEOUT_MS): Promise<T> {
  const method = init?.method ?? "GET";
  const endpointTemplate = sanitizeEndpoint(path);
  const actionId = consumePendingActionId();
  const screen = getCurrentScreen();
  const started = performance.now();

  recordEvent({
    event_id: newEventId(),
    timestamp: nowIso(),
    screen,
    kind: "REQUEST_STARTED",
    action_id: actionId,
    method,
    endpoint_template: endpointTemplate,
  });
  resolveAction(actionId);

  const controller = new AbortController();
  const timeoutTimer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
      signal: controller.signal,
    });
  } catch (e: unknown) {
    clearTimeout(timeoutTimer);
    const duration = Math.round(performance.now() - started);
    if (e instanceof DOMException && e.name === "AbortError") {
      recordEvent({
        event_id: newEventId(),
        timestamp: nowIso(),
        screen,
        kind: "REQUEST_TIMEOUT",
        action_id: actionId,
        method,
        endpoint_template: endpointTemplate,
        duration_ms: duration,
      });
      throw new Error("Żądanie przekroczyło limit czasu.");
    }
    recordEvent({
      event_id: newEventId(),
      timestamp: nowIso(),
      screen,
      kind: "REQUEST_FAILED",
      action_id: actionId,
      method,
      endpoint_template: endpointTemplate,
      status: null,
      error_category: "network",
      duration_ms: duration,
    });
    throw e;
  }
  clearTimeout(timeoutTimer);
  const duration = Math.round(performance.now() - started);

  if (!res.ok) {
    recordEvent({
      event_id: newEventId(),
      timestamp: nowIso(),
      screen,
      kind: "REQUEST_FAILED",
      action_id: actionId,
      method,
      endpoint_template: endpointTemplate,
      status: res.status,
      error_category: res.status >= 500 ? "http_5xx" : "http_4xx",
      duration_ms: duration,
    });
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `${res.status} ${res.statusText}`);
  }

  // R1-3 (round-1 audit): an HTTP-successful response can still fail to
  // parse -- that must be REQUEST_FAILED(error_category="parse"), not
  // REQUEST_SUCCEEDED. Classify only after parsing actually succeeds.
  if (res.status === 204) {
    recordEvent({
      event_id: newEventId(),
      timestamp: nowIso(),
      screen,
      kind: "REQUEST_SUCCEEDED",
      action_id: actionId,
      method,
      endpoint_template: endpointTemplate,
      status: res.status,
      duration_ms: duration,
    });
    return undefined as T;
  }

  let data: T;
  try {
    data = (await res.json()) as T;
  } catch {
    recordEvent({
      event_id: newEventId(),
      timestamp: nowIso(),
      screen,
      kind: "REQUEST_FAILED",
      action_id: actionId,
      method,
      endpoint_template: endpointTemplate,
      status: res.status,
      error_category: "parse",
      duration_ms: duration,
    });
    throw new Error("Nieprawidłowa odpowiedź serwera.");
  }

  recordEvent({
    event_id: newEventId(),
    timestamp: nowIso(),
    screen,
    kind: "REQUEST_SUCCEEDED",
    action_id: actionId,
    method,
    endpoint_template: endpointTemplate,
    status: res.status,
    duration_ms: duration,
  });
  return data;
}

export const api = {
  listSites: (includeInactive = false) =>
    req<SiteSummary[]>(`/workspace/sites${includeInactive ? "?include_inactive=true" : ""}`),

  createSite: (payload: CreateSiteRequest) =>
    req<CreateSiteResponse>("/workspace/sites", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  deactivateSite: (siteId: string) => req<void>(`/workspace/sites/${siteId}/deactivate`, { method: "POST" }),
  reactivateSite: (siteId: string) => req<void>(`/workspace/sites/${siteId}/reactivate`, { method: "POST" }),

  // Shift catalog (Panel sterowania -> Obiekt, T030)
  getShiftCatalog: (siteId: string) => req<ShiftCatalogOut>(`/workspace/sites/${siteId}/shift-catalog`),
  putShiftCatalog: (siteId: string, shifts: ShiftRowIn[]) =>
    req<void>(`/workspace/sites/${siteId}/shift-catalog`, { method: "PUT", body: JSON.stringify({ shifts }) }),

  // Planowanie miesiąca (T031)
  getScheduleMonths: (siteId: string) => req<{ months: string[] }>(`/workspace/sites/${siteId}/schedule/months`),
  getMonthView: (siteId: string, month: string) => req<MonthViewOut>(`/workspace/sites/${siteId}/schedule/${month}`),
  getPrecheck: (siteId: string, month: string) => req<PrecheckOut>(`/workspace/sites/${siteId}/schedule/${month}/precheck`),
  planMonth: (siteId: string, month: string, effectiveFrom: string | null, searchAttempt = 0) =>
    req<PlanningResultOut>(`/workspace/sites/${siteId}/schedule/${month}/plan`, {
      method: "POST",
      body: JSON.stringify({ effective_from: effectiveFrom, search_attempt: searchAttempt }),
    }, PLANNING_REQUEST_TIMEOUT_MS),
  selectCandidate: (siteId: string, month: string, candidate: AssignmentIn[], note?: string) =>
    req<void>(`/workspace/sites/${siteId}/schedule/${month}/select-candidate`, {
      method: "POST",
      body: JSON.stringify({ candidate, note: note ?? null }),
    }),
  replanMonth: (siteId: string, month: string, effectiveFrom: string, note?: string) =>
    req<PlanningResultOut>(`/workspace/sites/${siteId}/schedule/${month}/replan`, {
      method: "POST",
      body: JSON.stringify({ effective_from: effectiveFrom, note: note ?? null }),
    }, PLANNING_REQUEST_TIMEOUT_MS),
  replanWiderSearch: (siteId: string, month: string, searchAttempt = 0) =>
    req<PlanningResultOut>(`/workspace/sites/${siteId}/schedule/${month}/replan/wider-search`, {
      method: "POST",
      body: JSON.stringify({ search_attempt: searchAttempt }),
    }, PLANNING_REQUEST_TIMEOUT_MS),
  replanRetry: (siteId: string, month: string, searchAttempt = 0) =>
    req<PlanningResultOut>(`/workspace/sites/${siteId}/schedule/${month}/replan/retry`, {
      method: "POST",
      body: JSON.stringify({ search_attempt: searchAttempt }),
    }, PLANNING_REQUEST_TIMEOUT_MS),
  finalizeMonth: (siteId: string, month: string, acknowledgedDeviationIds: string[], reason?: string) =>
    req<void>(`/workspace/sites/${siteId}/schedule/${month}/finalize`, {
      method: "POST",
      body: JSON.stringify({ acknowledged_deviation_ids: acknowledgedDeviationIds, reason: reason ?? null }),
    }),
  restoreVersion: (siteId: string, month: string, versionId: string, note?: string) =>
    req<void>(`/workspace/sites/${siteId}/schedule/${month}/restore`, {
      method: "POST",
      body: JSON.stringify({ version_id: versionId, note: note ?? null }),
    }),
  excludeVersionFromHistory: (siteId: string, month: string, versionId: string) =>
    req<void>(`/workspace/sites/${siteId}/schedule/${month}/exclude-from-history`, {
      method: "POST",
      body: JSON.stringify({ version_id: versionId }),
    }),

  getCalendarRange: (start: string, end: string) =>
    req<CalendarDayOut[]>(`/workspace/calendar?start=${start}&end=${end}`),

  setCalendarDay: (date: string, holiday: boolean, site_id: string) =>
    req<void>("/workspace/calendar/day", {
      method: "POST",
      body: JSON.stringify({ date, holiday, site_id }),
    }),

  downloadBackup: () => downloadPost("/workspace/backup"),
  downloadDiagnostics: () => {
    let body: string | undefined;
    try {
      body = JSON.stringify({ frontend_report: getFrontendReport() });
    } catch {
      // Building the frontend report must never block the existing
      // backend diagnostics download (brief.md section 3.4).
      body = undefined;
    }
    return downloadPost("/workspace/diagnostics", body);
  },

  // Roster (brief.md section 5.1)
  listRoster: (siteId: string) => req<RosterRow[]>(`/workspace/sites/${siteId}/roster`),
  listPickableEmployees: (siteId: string) => req<PickableEmployee[]>(`/workspace/sites/${siteId}/roster/pickable`),
  attachToRoster: (siteId: string, employeeId: string) =>
    req<void>(`/workspace/sites/${siteId}/roster`, { method: "POST", body: JSON.stringify({ employee_id: employeeId }) }),
  updateRosterRow: (siteId: string, employeeId: string, payload: { enabled?: boolean; can_work_24h?: boolean }) =>
    req<void>(`/workspace/sites/${siteId}/roster/${employeeId}`, { method: "PATCH", body: JSON.stringify(payload) }),

  // Employee (brief.md section 5.1)
  createEmployee: (payload: { employee_id: string; site_id: string; display_name: string; day_only: boolean }) =>
    req<void>("/workspace/employees", { method: "POST", body: JSON.stringify(payload) }),
  getEmployeeDetail: (employeeId: string, siteId: string) =>
    req<EmployeeDetailOut>(`/workspace/employees/${employeeId}?site_id=${siteId}`),
  updateDayOnly: (employeeId: string, siteId: string, dayOnly: boolean) =>
    req<void>(`/workspace/employees/${employeeId}`, {
      method: "PATCH",
      body: JSON.stringify({ site_id: siteId, day_only: dayOnly }),
    }),

  // Availability -- Ogólna dostępność + Zgłoś nieobecność (same mechanism)
  createAvailability: (employeeId: string, payload: { site_id: string; availability_id: string; kind: string; start_date: string; end_date: string }) =>
    req<void>(`/workspace/employees/${employeeId}/availability`, { method: "POST", body: JSON.stringify(payload) }),
  updateAvailability: (employeeId: string, availabilityId: string, payload: { site_id: string; kind: string; start_date: string; end_date: string; active: boolean }) =>
    req<void>(`/workspace/employees/${employeeId}/availability/${availabilityId}`, { method: "PATCH", body: JSON.stringify(payload) }),

  // Target hours
  getTargetHours: (employeeId: string, month: string) =>
    req<{ target_hours: number | null }>(`/workspace/employees/${employeeId}/target-hours?month=${month}`),
  setTargetHours: (employeeId: string, payload: { site_id: string; month: string; target_hours: number }) =>
    req<void>(`/workspace/employees/${employeeId}/target-hours`, { method: "POST", body: JSON.stringify(payload) }),

  // Dniówka/Nocka/weekday matrix (T021b-backed)
  getEmployeeMatrix: (employeeId: string, siteId: string, month: string) =>
    req<{ cells: MatrixCellOut[] }>(`/workspace/employees/${employeeId}/matrix?site_id=${siteId}&month=${month}`),
  createShiftUnavailability: (employeeId: string, payload: { site_id: string; shift_kind: "D" | "N"; effective_from: string; effective_to?: string | null }) =>
    req<void>(`/workspace/employees/${employeeId}/matrix/shift-unavailability`, { method: "POST", body: JSON.stringify(payload) }),
  createWeekdayUnavailability: (employeeId: string, payload: { site_id: string; iso_weekday: number; effective_from: string; effective_to?: string | null }) =>
    req<void>(`/workspace/employees/${employeeId}/matrix/weekday-unavailability`, { method: "POST", body: JSON.stringify(payload) }),
  createDayOnlyException: (employeeId: string, payload: { site_id: string; effective_from: string; effective_to?: string | null }) =>
    req<void>(`/workspace/employees/${employeeId}/matrix/day-only-exception`, { method: "POST", body: JSON.stringify(payload) }),
  updateMatrixRule: (employeeId: string, ruleId: string, payload: { site_id: string; effective_from: string; effective_to?: string | null }) =>
    req<void>(`/workspace/employees/${employeeId}/matrix/${ruleId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  endMatrixRuleEarly: (employeeId: string, ruleId: string, payload: { site_id: string; effective_from: string }) =>
    req<void>(`/workspace/employees/${employeeId}/matrix/${ruleId}/end-early`, { method: "POST", body: JSON.stringify(payload) }),

  // Analityka i bilanse (T021)
  getAnalytics: (siteId: string, month: string) =>
    req<CoordinatorAnalyticsViewOut>(`/workspace/sites/${siteId}/analytics?month=${month}`),

  // Historia i audyt (T021)
  getActionHistory: (siteId: string, actionKind?: CoordinatorActionKind) =>
    req<MaterialActionSummaryOut[]>(
      `/workspace/sites/${siteId}/history/actions${actionKind ? `?action_kind=${actionKind}` : ""}`,
    ),
  getActionDetail: (actionId: string) => req<MaterialActionDetailOut>(`/workspace/history/actions/${actionId}`),
  getRuleHistory: (siteId: string) => req<Record<string, DecisionRecordOut[]>>(`/workspace/sites/${siteId}/history/rules`),

  // Decyzje koordynatora (T021)
  getDecisionMonths: (siteId: string) => req<{ months: string[] }>(`/workspace/sites/${siteId}/decisions/months`),
  getDecisionForMonth: (siteId: string, month: string) =>
    req<DecisionRequiredOut | null>(`/workspace/sites/${siteId}/decisions/${month}`),
};

async function downloadPost(path: string, body?: string): Promise<void> {
  const res = await fetch(`/api${path}`, {
    method: "POST",
    ...(body ? { headers: { "Content-Type": "application/json" }, body } : {}),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const filename = match?.[1] ?? "download";
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
