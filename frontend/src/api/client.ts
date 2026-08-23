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
