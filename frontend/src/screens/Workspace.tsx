import { useEffect, useMemo, useState } from "react";
import { api, CalendarDayOut, SiteSummary } from "../api/client";

type FilterChip = "ALL" | "DECISION_REQUIRED" | "CONFIG_INCOMPLETE";
type Regime = "OCHRONA" | "ORDINARY";

const today = new Date();
const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
const monthEnd = new Date(today.getFullYear(), today.getMonth() + 1, 0);
const iso = (d: Date) => d.toISOString().slice(0, 10);

export default function Workspace() {
  const [sites, setSites] = useState<SiteSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<FilterChip>("ALL");
  const [creatingRegime, setCreatingRegime] = useState<Regime | null>(null);
  const [calendarOpen, setCalendarOpen] = useState(false);

  const loadSites = () => {
    setLoading(true);
    api
      .listSites()
      .then(setSites)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  };

  useEffect(loadSites, []);

  const filtered = useMemo(() => {
    let result = sites;
    if (filter === "DECISION_REQUIRED") {
      result = result.filter((s) => s.decision_required_months.length > 0);
    } else if (filter === "CONFIG_INCOMPLETE") {
      result = result.filter((s) => !s.complete || s.print_settings_missing);
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter(
        (s) => s.display_name.toLowerCase().includes(q) || s.site_id.toLowerCase().includes(q),
      );
    }
    return result;
  }, [sites, filter, search]);

  return (
    <div className="workspace">
      <header className="workspace-header">
        <h1>Przedpokój</h1>
        <div className="header-actions">
          <button onClick={() => setCalendarOpen(true)}>Kalendarz</button>
          <button onClick={() => api.downloadBackup().catch((e) => setError(String(e.message ?? e)))}>
            Kopia zapasowa
          </button>
          <button onClick={() => api.downloadDiagnostics().catch((e) => setError(String(e.message ?? e)))}>
            Diagnostyka
          </button>
        </div>
      </header>

      {error && <div className="banner-error">{error}</div>}

      <div className="toolbar">
        <input
          type="text"
          placeholder="Szukaj obiektu…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="chips">
          <Chip label="Wszystkie" active={filter === "ALL"} onClick={() => setFilter("ALL")} />
          <Chip
            label="Wymaga decyzji"
            active={filter === "DECISION_REQUIRED"}
            onClick={() => setFilter("DECISION_REQUIRED")}
          />
          <Chip
            label="Konfiguracja niepełna"
            active={filter === "CONFIG_INCOMPLETE"}
            onClick={() => setFilter("CONFIG_INCOMPLETE")}
          />
        </div>
        <div className="create-actions">
          <button onClick={() => setCreatingRegime("OCHRONA")}>+ Obiekt (Ochrona)</button>
          <button onClick={() => setCreatingRegime("ORDINARY")}>+ Obiekt (Zwykły)</button>
        </div>
      </div>

      {loading ? (
        <p>Ładowanie…</p>
      ) : (
        <ul className="site-list">
          {filtered.map((site) => (
            <SiteRow key={site.site_id} site={site} />
          ))}
          {filtered.length === 0 && <li className="empty">Brak obiektów spełniających kryteria.</li>}
        </ul>
      )}

      {creatingRegime && (
        <CreateSiteModal
          regime={creatingRegime}
          onClose={() => setCreatingRegime(null)}
          onCreated={() => {
            setCreatingRegime(null);
            loadSites();
          }}
        />
      )}

      {calendarOpen && sites.length > 0 && (
        <CalendarModal siteIdForAuth={sites[0].site_id} onClose={() => setCalendarOpen(false)} />
      )}
      {calendarOpen && sites.length === 0 && (
        <div className="modal-backdrop" onClick={() => setCalendarOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <p>Kalendarz wymaga co najmniej jednego obiektu (autoryzacja zapisu).</p>
            <button onClick={() => setCalendarOpen(false)}>Zamknij</button>
          </div>
        </div>
      )}
    </div>
  );
}

function Chip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button className={active ? "chip chip-active" : "chip"} onClick={onClick}>
      {label}
    </button>
  );
}

function SiteRow({ site }: { site: SiteSummary }) {
  return (
    <li className="site-row">
      <div className="site-main">
        <span className="site-name">{site.display_name}</span>
        <span className={`regime-badge regime-${site.planning_regime.toLowerCase()}`}>
          {site.planning_regime === "OCHRONA" ? "Ochrona" : "Zwykły"}
        </span>
      </div>
      <div className="site-flags">
        {!site.complete && <span className="flag flag-warning">Konfiguracja niepełna</span>}
        {site.print_settings_missing && <span className="flag flag-warning">Brak ustawień wydruku</span>}
        {site.decision_required_months.length > 0 && (
          <span className="flag flag-alert">Wymaga decyzji: {site.decision_required_months.join(", ")}</span>
        )}
        {site.complete && !site.print_settings_missing && site.decision_required_months.length === 0 && (
          <span className="flag flag-ok">Gotowy</span>
        )}
      </div>
      {!site.complete && site.missing.length > 0 && (
        <ul className="missing-list">
          {site.missing.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      )}
    </li>
  );
}

function CreateSiteModal({
  regime,
  onClose,
  onCreated,
}: {
  regime: Regime;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [displayName, setDisplayName] = useState("");
  const [profileName, setProfileName] = useState("");
  const [threshold, setThreshold] = useState(40);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await api.createSite({
        display_name: displayName,
        profile_display_name: profileName,
        rolling_7d_decision_threshold_hours: threshold,
        planning_regime: regime,
      });
      onCreated();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Nowy obiekt — {regime === "OCHRONA" ? "Ochrona" : "Zwykły"}</h2>
        {error && <div className="banner-error">{error}</div>}
        <label>
          Nazwa obiektu
          <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        </label>
        <label>
          Nazwa profilu zmianowego
          <input value={profileName} onChange={(e) => setProfileName(e.target.value)} />
        </label>
        <label>
          Próg decyzyjny 7-dniowy (godziny)
          <input
            type="number"
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
          />
        </label>
        <div className="modal-actions">
          <button onClick={onClose} disabled={submitting}>
            Anuluj
          </button>
          <button
            onClick={submit}
            disabled={submitting || !displayName.trim() || !profileName.trim()}
          >
            {submitting ? "Tworzenie…" : "Utwórz"}
          </button>
        </div>
      </div>
    </div>
  );
}

function CalendarModal({ siteIdForAuth, onClose }: { siteIdForAuth: string; onClose: () => void }) {
  const [days, setDays] = useState<Map<string, boolean>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    api
      .getCalendarRange(iso(monthStart), iso(monthEnd))
      .then((rows: CalendarDayOut[]) => {
        const m = new Map<string, boolean>();
        rows.forEach((r) => m.set(r.date, r.holiday));
        setDays(m);
      })
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const dates: Date[] = [];
  for (let d = new Date(monthStart); d <= monthEnd; d.setDate(d.getDate() + 1)) {
    dates.push(new Date(d));
  }

  const toggle = async (dateIso: string, currentHoliday: boolean | undefined) => {
    try {
      await api.setCalendarDay(dateIso, !(currentHoliday ?? false), siteIdForAuth);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    }
  };

  const generate = async () => {
    try {
      await api.bulkGenerateCalendar(iso(monthStart), iso(monthEnd), siteIdForAuth);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
        <h2>
          Kalendarz — {monthStart.toLocaleString("pl-PL", { month: "long", year: "numeric" })}
        </h2>
        {error && <div className="banner-error">{error}</div>}
        <button onClick={generate}>
          Wygeneruj kalendarz na miesiąc {monthStart.toLocaleString("pl-PL", { month: "long", year: "numeric" })}
        </button>
        {loading ? (
          <p>Ładowanie…</p>
        ) : (
          <div className="calendar-grid">
            {dates.map((d) => {
              const dIso = iso(d);
              const has = days.has(dIso);
              const holiday = days.get(dIso);
              const state = !has ? "unconfigured" : holiday ? "holiday" : "workday";
              return (
                <button
                  key={dIso}
                  className={`calendar-day calendar-day-${state}`}
                  onClick={() => toggle(dIso, holiday)}
                  title={
                    state === "unconfigured"
                      ? "niekonfigurowany"
                      : state === "holiday"
                        ? "święto"
                        : "roboczy"
                  }
                >
                  {d.getDate()}
                </button>
              );
            })}
          </div>
        )}
        <div className="calendar-legend">
          <span className="legend-item"><i className="calendar-day-unconfigured" /> niekonfigurowany</span>
          <span className="legend-item"><i className="calendar-day-workday" /> roboczy</span>
          <span className="legend-item"><i className="calendar-day-holiday" /> święto</span>
        </div>
        <div className="modal-actions">
          <button onClick={onClose}>Zamknij</button>
        </div>
      </div>
    </div>
  );
}
