import { useEffect, useMemo, useState } from "react";
import { api, CalendarDayOut, SiteSummary } from "../api/client";
import { translateMissingReason } from "../api/completeness";

type FilterChip = "ALL" | "DECISION_REQUIRED" | "CONFIG_INCOMPLETE";
type Regime = "OCHRONA" | "ORDINARY";

const today = new Date();
const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
const monthEnd = new Date(today.getFullYear(), today.getMonth() + 1, 0);
const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

const isConfigComplete = (s: SiteSummary) => s.complete && !s.print_settings_missing;

export default function Workspace({ onOpenSite }: { onOpenSite: (siteId: string, siteName: string) => void }) {
  const [sites, setSites] = useState<SiteSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<FilterChip>("ALL");
  const [creatingRegime, setCreatingRegime] = useState<Regime | null>(null);
  const [showRemoved, setShowRemoved] = useState(false);
  const [removedSites, setRemovedSites] = useState<SiteSummary[]>([]);
  const [busySiteId, setBusySiteId] = useState<string | null>(null);
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    try {
      return (localStorage.getItem("elnath-rota-theme") as "dark" | "light") ?? "dark";
    } catch {
      return "dark";
    }
  });

  useEffect(() => {
    if (theme === "light") {
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    try {
      localStorage.setItem("elnath-rota-theme", theme);
    } catch {
      // per-viewer convenience only; ignore storage failures
    }
  }, [theme]);

  const loadSites = () => {
    setLoading(true);
    api
      .listSites()
      .then(setSites)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  };

  const loadRemovedSites = () => {
    api
      .listSites(true)
      .then((all) => setRemovedSites(all.filter((s) => !s.active)))
      .catch((e) => setError(String(e.message ?? e)));
  };

  useEffect(loadSites, []);

  useEffect(() => {
    if (showRemoved) loadRemovedSites();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showRemoved]);

  // 2026-08-26 owner decision: usuwanie obiektu z Workspace bez usuwania go
  // z historii programu -- Site.active toggles, nothing is deleted.
  const deactivateSite = (site: SiteSummary) => {
    if (!window.confirm(`Usunąć obiekt „${site.display_name}” z Workspace? Cała historia zostanie zachowana.`)) return;
    setBusySiteId(site.site_id);
    api
      .deactivateSite(site.site_id)
      .then(loadSites)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setBusySiteId(null));
  };

  const reactivateSite = (site: SiteSummary) => {
    setBusySiteId(site.site_id);
    api
      .reactivateSite(site.site_id)
      .then(() => {
        loadSites();
        loadRemovedSites();
      })
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setBusySiteId(null));
  };

  const decisionCount = sites.filter((s) => s.decision_required_months.length > 0).length;
  const incompleteCount = sites.filter((s) => !isConfigComplete(s)).length;

  const filtered = useMemo(() => {
    let result = sites;
    if (filter === "DECISION_REQUIRED") {
      result = result.filter((s) => s.decision_required_months.length > 0);
    } else if (filter === "CONFIG_INCOMPLETE") {
      result = result.filter((s) => !isConfigComplete(s));
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
      <div className="topbar">
        <div className="topbar-brand">
          <div className="topbar-brand-mark">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M12 2v6M12 16v6M2 12h6M16 12h6" />
            </svg>
          </div>
          <span className="brand-font topbar-brand-name">Elnath Rota</span>
        </div>
        <div className="topbar-search">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.3-4.3" />
          </svg>
          <input
            type="text"
            placeholder="Szukaj obiektu…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="topbar-actions">
          <button className="icon-button" title="Kalendarz (dni robocze i święta)" onClick={() => setCalendarOpen(true)}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="4" width="18" height="17" rx="2" />
              <path d="M3 9h18M8 3v3M16 3v3" />
            </svg>
          </button>
          <button
            className="icon-button"
            title={theme === "light" ? "Przełącz na ciemny motyw" : "Przełącz na jasny motyw"}
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          >
            {theme === "light" ? (
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
              </svg>
            ) : (
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z" />
              </svg>
            )}
          </button>
          <div className="topbar-user">
            <div className="topbar-user-avatar">K</div>
            <span className="topbar-user-name">Koordynator</span>
          </div>
        </div>
      </div>

      <div className="workspace-body">
        <div className="workspace-content">
          {error && <div className="banner-error">{error}</div>}

          <div className="workspace-title-row">
            <h1 className="brand-font">Twoje obiekty</h1>
            <div className="workspace-title-actions">
              <span className="site-count">{sites.length} obiektów</span>
              <button className="btn-ghost" data-diag-action="toggle-removed-sites" onClick={() => setShowRemoved((s) => !s)}>
                {showRemoved ? "Ukryj usunięte" : "Usunięte obiekty"}
              </button>
              <button className="btn-primary" data-diag-action="create-site-open" onClick={() => setCreatingRegime("OCHRONA")}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M12 5v14M5 12h14" />
                </svg>
                Nowy obiekt (Ochrona)
              </button>
              <button className="btn-primary" onClick={() => setCreatingRegime("ORDINARY")}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M12 5v14M5 12h14" />
                </svg>
                Nowy obiekt (Standardowy)
              </button>
            </div>
          </div>
          <p className="workspace-subtitle">Wybierz obiekt, żeby wejść do jego grafiku, konfiguracji i decyzji.</p>

          {creatingRegime && (
            <CreatePanel
              regime={creatingRegime}
              onClose={() => setCreatingRegime(null)}
              onCreated={() => {
                setCreatingRegime(null);
                loadSites();
              }}
            />
          )}

          <div className="chip-row">
            <Chip label={`Wszystkie (${sites.length})`} active={filter === "ALL"} onClick={() => setFilter("ALL")} />
            <Chip
              label={`Wymaga decyzji (${decisionCount})`}
              tip="Miesiące, w których trzeba coś zdecydować — np. bo w danym tygodniu przekroczono dopuszczalną liczbę godzin."
              rust
              active={filter === "DECISION_REQUIRED"}
              onClick={() => setFilter("DECISION_REQUIRED")}
            />
            <Chip
              label={`Konfiguracja niepełna (${incompleteCount})`}
              tip="Obiekt nie jest jeszcze gotowy do pracy — brakuje np. grafiku zmian, przypisanych pracowników albo ustawień wydruku."
              active={filter === "CONFIG_INCOMPLETE"}
              onClick={() => setFilter("CONFIG_INCOMPLETE")}
            />
          </div>

          {loading ? (
            <p>Ładowanie…</p>
          ) : (
            <ul className="site-grid">
              {filtered.map((site) => (
                <SiteRow
                  key={site.site_id}
                  site={site}
                  onOpen={() => onOpenSite(site.site_id, site.display_name)}
                  onDeactivate={() => deactivateSite(site)}
                  busy={busySiteId === site.site_id}
                />
              ))}
              {filtered.length === 0 && <li className="empty-state">Brak obiektów spełniających kryteria.</li>}
            </ul>
          )}

          {showRemoved && (
            <div className="panel" style={{ marginTop: 12 }}>
              <h3>Usunięte obiekty</h3>
              <p className="panel-hint">
                Nie widoczne w Workspace, ale cała historia (grafiki, pracownicy, decyzje) jest zachowana.
              </p>
              {removedSites.length === 0 ? (
                <p className="panel-hint">Brak usuniętych obiektów.</p>
              ) : (
                <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                  {removedSites.map((site) => (
                    <li key={site.site_id} style={{ padding: "6px 0", display: "flex", alignItems: "center", gap: 8 }}>
                      <span>{site.display_name}</span>
                      <button
                        className="btn-ghost"
                        data-diag-action="reactivate-site"
                        onClick={() => reactivateSite(site)}
                        disabled={busySiteId === site.site_id}
                      >
                        Przywróć
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <div className="utility-panel">
            <div>
              <h3>Kopia zapasowa i diagnostyka</h3>
              <p>Obejmuje wszystkie obiekty naraz — całą bazę danych, nie tylko wybrany obiekt.</p>
            </div>
            <div className="utility-panel-actions">
              <button
                className="btn-secondary"
                data-diag-action="download-diagnostics"
                onClick={() => api.downloadDiagnostics().catch((e) => setError(String(e.message ?? e)))}
              >
                Pobierz pakiet diagnostyczny
              </button>
              <button
                className="btn-primary"
                data-diag-action="download-backup"
                onClick={() => api.downloadBackup().catch((e) => setError(String(e.message ?? e)))}
              >
                Utwórz kopię zapasową
              </button>
            </div>
          </div>
        </div>
      </div>

      {calendarOpen && sites.length > 0 && (
        <CalendarModal siteIdForAuth={sites[0].site_id} onClose={() => setCalendarOpen(false)} />
      )}
      {calendarOpen && sites.length === 0 && (
        <div className="modal-backdrop" onClick={() => setCalendarOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <p>Kalendarz wymaga co najmniej jednego obiektu (autoryzacja zapisu).</p>
            <button className="btn-ghost" onClick={() => setCalendarOpen(false)}>
              Zamknij
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Chip({
  label,
  tip,
  rust,
  active,
  onClick,
}: {
  label: string;
  tip?: string;
  rust?: boolean;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`chip${active ? " chip-active" : ""}${rust && !active ? " chip-rust" : ""}`}
      onClick={onClick}
    >
      {label}
      {tip && <InfoTip text={tip} />}
    </button>
  );
}

function InfoTip({ text }: { text: string }) {
  return (
    <span className="info-tip" title={text} onClick={(e) => e.stopPropagation()}>
      ?
    </span>
  );
}

function SiteRow({
  site, onOpen, onDeactivate, busy,
}: {
  site: SiteSummary;
  onOpen: () => void;
  onDeactivate: () => void;
  busy: boolean;
}) {
  const needsDecision = site.decision_required_months.length > 0;
  const complete = isConfigComplete(site);
  const translatedMissing = site.missing.map(translateMissingReason);

  const tone = needsDecision ? "rust" : !complete ? "slate" : "sage";
  const statusLabel = needsDecision
    ? site.decision_required_months.length === 1
      ? "1 decyzja"
      : `${site.decision_required_months.length} decyzje`
    : !complete
      ? "Konfiguracja"
      : "Gotowy";

  const missingSummary = !complete
    ? translatedMissing[0] ?? (site.print_settings_missing ? "Brak ustawień wydruku" : "")
    : "";

  return (
    <li
      className={`site-card${!complete ? " site-card-incomplete" : ""}`}
      onClick={onOpen}
      role="button"
      tabIndex={0}
      data-diag-action="site-row-open"
    >
      <div className="site-card-top">
        <div className={`site-card-icon icon-${tone}`}>
          <StatusIcon tone={tone} />
        </div>
        <span className={`site-card-status status-${tone}`}>{statusLabel}</span>
        <button
          className="btn-ghost"
          data-diag-action="deactivate-site"
          disabled={busy}
          onClick={(e) => {
            e.stopPropagation();
            onDeactivate();
          }}
        >
          Usuń
        </button>
      </div>
      <div>
        <h3 className="site-card-name">{site.display_name}</h3>
        <p className="site-card-regime">
          {site.planning_regime === "OCHRONA" ? "Ochrona obiektu" : "Obiekt standardowy"}
        </p>
      </div>
      <div className="site-card-foot">
        <span>{needsDecision ? site.decision_required_months.join(", ") : missingSummary || "Bez zaległości"}</span>
      </div>
      {!complete && translatedMissing.length > 0 && (
        <ul className="site-card-missing">
          {translatedMissing.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      )}
    </li>
  );
}

function StatusIcon({ tone }: { tone: "rust" | "sage" | "slate" }) {
  if (tone === "rust") {
    return (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="var(--rust)" strokeWidth="2">
        <path d="M12 9v4M12 17h.01" />
        <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
      </svg>
    );
  }
  if (tone === "sage") {
    return (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="var(--sage)" strokeWidth="2">
        <path d="M20 6 9 17l-5-5" />
      </svg>
    );
  }
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="var(--slate)" strokeWidth="2">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v4M12 16h.01" />
    </svg>
  );
}

function CreatePanel({
  regime,
  onClose,
  onCreated,
}: {
  regime: Regime;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [displayName, setDisplayName] = useState("");
  const [threshold, setThreshold] = useState(40);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await api.createSite({
        display_name: displayName,
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
    <div className="create-panel">
      <h3>Nowy obiekt — {regime === "OCHRONA" ? "Ochrona" : "Standardowy"}</h3>
      <p className="create-panel-hint">
        Tworzy minimalny wpis — obiekt pojawi się od razu w „Konfiguracja niepełna” i czeka na katalog zmian,
        obsadę i ustawienia wydruku w Panelu sterowania.
      </p>
      {error && <div className="banner-error">{error}</div>}
      <div className="create-panel-fields">
        <label>
          <span className="field-label">Nazwa obiektu</span>
          <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="np. NORDPLAST II" />
        </label>
        <label>
          <span className="field-label">Próg decyzyjny 7-dniowy</span>
          <input type="number" value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} />
          <span className="field-hint">
            Gdy w dowolnym 7-dniowym oknie suma godzin przekroczy tę wartość, system oznaczy dany miesiąc jako
            „Wymaga decyzji”.
          </span>
        </label>
      </div>
      <div className="create-panel-actions">
        <button
          className="btn-primary"
          data-diag-action="create-site-submit"
          onClick={submit}
          disabled={submitting || !displayName.trim()}
        >
          {submitting ? "Tworzenie…" : "Utwórz obiekt"}
        </button>
        <button className="btn-ghost" onClick={onClose} disabled={submitting}>
          Anuluj
        </button>
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
      const missingDates = dates.map(iso).filter((d) => !days.has(d));
      for (const dateIso of missingDates) {
        await api.setCalendarDay(dateIso, false, siteIdForAuth);
      }
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
        <h2>Kalendarz — {monthStart.toLocaleString("pl-PL", { month: "long", year: "numeric" })}</h2>
        {error && <div className="banner-error">{error}</div>}
        <button className="btn-secondary" onClick={generate}>
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
                  title={state === "unconfigured" ? "niekonfigurowany" : state === "holiday" ? "święto" : "roboczy"}
                >
                  {d.getDate()}
                </button>
              );
            })}
          </div>
        )}
        <div className="calendar-legend">
          <span className="legend-item">
            <i className="calendar-day" /> niekonfigurowany
          </span>
          <span className="legend-item">
            <i className="calendar-day calendar-day-workday" /> roboczy
          </span>
          <span className="legend-item">
            <i className="calendar-day calendar-day-holiday" /> święto
          </span>
        </div>
        <div className="modal-actions">
          <button className="btn-ghost" onClick={onClose}>
            Zamknij
          </button>
        </div>
      </div>
    </div>
  );
}
