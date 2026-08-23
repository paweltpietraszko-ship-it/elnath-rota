// Thin fetch wrapper over api/routers/*. Mirrors the response shapes
// exactly (see api/routers/bootstrap.py, calendar.py, backup.py) --
// no client-side reinterpretation of business fields.

export interface SiteSummary {
  site_id: string;
  display_name: string;
  planning_regime: "OCHRONA" | "ORDINARY";
  complete: boolean;
  missing: string[];
  decision_required_months: string[];
  print_settings_missing: boolean;
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

export interface CalendarDayOut {
  date: string;
  holiday: boolean;
}

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

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  listSites: () => req<SiteSummary[]>("/workspace/sites"),

  createSite: (payload: CreateSiteRequest) =>
    req<CreateSiteResponse>("/workspace/sites", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getCalendarRange: (start: string, end: string) =>
    req<CalendarDayOut[]>(`/workspace/calendar?start=${start}&end=${end}`),

  setCalendarDay: (date: string, holiday: boolean, site_id: string) =>
    req<void>("/workspace/calendar/day", {
      method: "POST",
      body: JSON.stringify({ date, holiday, site_id }),
    }),

  downloadBackup: () => downloadPost("/workspace/backup"),
  downloadDiagnostics: () => downloadPost("/workspace/diagnostics"),

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
  createShiftUnavailability: (employeeId: string, payload: { site_id: string; shift_kind: "D" | "N"; effective_from: string; effective_to: string }) =>
    req<void>(`/workspace/employees/${employeeId}/matrix/shift-unavailability`, { method: "POST", body: JSON.stringify(payload) }),
  createWeekdayUnavailability: (employeeId: string, payload: { site_id: string; iso_weekday: number; effective_from: string; effective_to: string }) =>
    req<void>(`/workspace/employees/${employeeId}/matrix/weekday-unavailability`, { method: "POST", body: JSON.stringify(payload) }),
  createDayOnlyException: (employeeId: string, payload: { site_id: string; effective_from: string; effective_to: string }) =>
    req<void>(`/workspace/employees/${employeeId}/matrix/day-only-exception`, { method: "POST", body: JSON.stringify(payload) }),
  updateMatrixRule: (employeeId: string, ruleId: string, payload: { site_id: string; effective_from: string; effective_to: string }) =>
    req<void>(`/workspace/employees/${employeeId}/matrix/${ruleId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  endMatrixRuleEarly: (employeeId: string, ruleId: string, payload: { site_id: string; effective_from: string }) =>
    req<void>(`/workspace/employees/${employeeId}/matrix/${ruleId}/end-early`, { method: "POST", body: JSON.stringify(payload) }),
};

async function downloadPost(path: string): Promise<void> {
  const res = await fetch(`/api${path}`, { method: "POST" });
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
