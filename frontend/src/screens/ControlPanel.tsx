import { useEffect, useState } from "react";
import type { View } from "../App";
import { api, PickableEmployee, RosterRow } from "../api/client";

export default function ControlPanel({
  siteId,
  siteName,
  onNavigate,
}: {
  siteId: string;
  siteName: string;
  onNavigate: (v: View) => void;
}) {
  const [roster, setRoster] = useState<RosterRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [showRemoved, setShowRemoved] = useState(false);

  const load = () => {
    setLoading(true);
    api
      .listRoster(siteId)
      .then(setRoster)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [siteId]);

  const toggle24h = async (employeeId: string, current: boolean) => {
    try {
      await api.updateRosterRow(siteId, employeeId, { can_work_24h: !current });
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    }
  };

  const removeFromRoster = async (employeeId: string) => {
    try {
      await api.updateRosterRow(siteId, employeeId, { enabled: false });
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    }
  };

  const visibleRoster = roster.filter((row) => row.enabled || showRemoved);

  return (
    <>
      <h1 className="brand-font" style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>
        Panel sterowania
      </h1>
      <p style={{ color: "var(--ink-soft)", fontSize: "13.5px", marginBottom: 24 }}>
        Konfigurator obiektu i obsady — dane trwałe, niezależne od miesiąca.
      </p>

      <div className="tab-row">
        <button className="tab-item" disabled title="jeszcze nie zbudowane">
          Obiekt
        </button>
        <button className="tab-item tab-item-active">Obsada ({roster.filter((r) => r.enabled).length})</button>
      </div>

      {error && <div className="banner-error">{error}</div>}

      <div className="panel">
        <div className="panel-title-row">
          <div>
            <h3>Lista pracowników</h3>
            <p className="panel-hint">Kliknij nazwisko, żeby otworzyć konfigurację pracownika.</p>
          </div>
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--ink-soft)" }}>
              <input
                type="checkbox"
                checked={showRemoved}
                onChange={(e) => setShowRemoved(e.target.checked)}
                style={{ width: "auto" }}
              />
              Pokaż usuniętych
            </label>
            <button className="btn-primary" onClick={() => setAddOpen(true)}>
              + Dodaj osobę
            </button>
          </div>
        </div>

        {addOpen && (
          <AddPersonPanel
            siteId={siteId}
            onClose={() => setAddOpen(false)}
            onAdded={(employeeId) => onNavigate({ screen: "employee", siteId, siteName, employeeId })}
          />
        )}

        {loading ? (
          <p>Ładowanie…</p>
        ) : (
          <div className="matrix-table-wrap">
            <table className="roster-table">
              <thead>
                <tr>
                  <th>Pracownik</th>
                  <th>Status</th>
                  <th>24h</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {visibleRoster.map((row) => (
                  <tr key={row.employee_id} className={row.enabled ? "" : "roster-row-disabled"}>
                    <td>
                      <button
                        className="roster-name-link"
                        onClick={() => onNavigate({ screen: "employee", siteId, siteName, employeeId: row.employee_id })}
                      >
                        {row.display_name}
                      </button>
                    </td>
                    <td>
                      <span className={`badge-pill ${row.enabled ? "badge-on" : "badge-off"}`}>
                        {row.enabled ? "na obsadzie" : "usunięty z obsady"}
                      </span>
                    </td>
                    <td>
                      <button
                        className={`matrix-box ${row.can_work_24h ? "matrix-box-on" : "matrix-box-off"}`}
                        onClick={() => toggle24h(row.employee_id, row.can_work_24h)}
                        title={row.can_work_24h ? "może pracować 24h" : "nie może pracować 24h"}
                      >
                        {row.can_work_24h ? "✓" : "✕"}
                      </button>
                    </td>
                    <td>
                      {row.enabled ? (
                        <button className="btn-ghost" onClick={() => removeFromRoster(row.employee_id)}>
                          Usuń z obsady
                        </button>
                      ) : (
                        <span style={{ color: "var(--ink-faint)", fontSize: 12 }}>
                          przywróć przez „+ Dodaj osobę”
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {visibleRoster.length === 0 && (
                  <tr>
                    <td colSpan={4} style={{ textAlign: "center", color: "var(--ink-faint)", padding: 20 }}>
                      {roster.length === 0
                        ? "Brak pracowników. Dodaj pierwszą osobę."
                        : "Brak aktywnych pracowników — wszyscy usunięci (włącz „Pokaż usuniętych”, żeby ich zobaczyć)."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

function newEmployeeIdStorageKey(siteId: string) {
  return `elnath-rota-new-employee-id:${siteId}`;
}

function AddPersonPanel({
  siteId,
  onClose,
  onAdded,
}: {
  siteId: string;
  onClose: () => void;
  onAdded: (employeeId: string) => void;
}) {
  const [mode, setMode] = useState<"new" | "existing">("new");
  const [displayName, setDisplayName] = useState("");
  const [dayOnly, setDayOnly] = useState(false);
  const [pickable, setPickable] = useState<PickableEmployee[]>([]);
  const [selectedExisting, setSelectedExisting] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Generated once (brief.md section 5.1, round-9 R9-1): held until the
  // attach step succeeds, surviving re-render, "Ponów" and a reload
  // (sessionStorage) -- never regenerated on retry, so a lost response
  // after Employee creation can never produce a second Employee.
  const [newEmployeeId] = useState<string>(() => {
    const key = newEmployeeIdStorageKey(siteId);
    try {
      const existing = sessionStorage.getItem(key);
      if (existing) return existing;
      const id = crypto.randomUUID();
      sessionStorage.setItem(key, id);
      return id;
    } catch {
      return crypto.randomUUID();
    }
  });

  useEffect(() => {
    if (mode === "existing") {
      api.listPickableEmployees(siteId).then(setPickable).catch((e) => setError(String(e.message ?? e)));
    }
  }, [mode, siteId]);

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "new") {
        await api.createEmployee({ employee_id: newEmployeeId, site_id: siteId, display_name: displayName, day_only: dayOnly });
        await api.attachToRoster(siteId, newEmployeeId);
        try {
          sessionStorage.removeItem(newEmployeeIdStorageKey(siteId));
        } catch {
          // per-viewer convenience only; ignore storage failures
        }
        onAdded(newEmployeeId);
      } else {
        if (!selectedExisting) throw new Error("Wybierz pracownika z listy.");
        await api.attachToRoster(siteId, selectedExisting);
        onAdded(selectedExisting);
      }
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="create-panel" style={{ marginBottom: 18 }}>
      <h3>Nowa osoba na obsadzie</h3>
      {error && <div className="banner-error">{error}</div>}
      <div className="chip-row" style={{ marginBottom: 14 }}>
        <button className={`chip${mode === "new" ? " chip-active" : ""}`} onClick={() => setMode("new")}>
          Nowy pracownik
        </button>
        <button className={`chip${mode === "existing" ? " chip-active" : ""}`} onClick={() => setMode("existing")}>
          Istniejący pracownik
        </button>
      </div>

      {mode === "new" ? (
        <div className="create-panel-fields" style={{ gridTemplateColumns: "1fr 1fr" }}>
          <label>
            <span className="field-label">Imię i nazwisko</span>
            <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="np. Jan Kowalski" />
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 18 }}>
            <input type="checkbox" checked={dayOnly} onChange={(e) => setDayOnly(e.target.checked)} style={{ width: "auto" }} />
            <span style={{ color: "var(--ink)", fontSize: 13 }}>Tylko dniówka (day_only)</span>
          </label>
        </div>
      ) : (
        <div style={{ marginBottom: 18 }}>
          <span className="field-label">Wybierz pracownika</span>
          <select
            value={selectedExisting}
            onChange={(e) => setSelectedExisting(e.target.value)}
            style={{
              width: "100%", background: "var(--paper-light)", border: "1px solid var(--line)",
              borderRadius: 8, padding: "9px 12px", fontSize: 13, color: "var(--ink)",
            }}
          >
            <option value="">— wybierz —</option>
            {pickable.map((p) => (
              <option key={p.employee_id} value={p.employee_id}>
                {p.display_name}
                {p.reason === "re-add" ? " (przywróć na obsadę)" : ""}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="create-panel-actions">
        <button
          className="btn-primary"
          onClick={submit}
          disabled={submitting || (mode === "new" ? !displayName.trim() : !selectedExisting)}
        >
          {submitting ? "Dodawanie…" : "Dodaj"}
        </button>
        <button className="btn-ghost" onClick={onClose} disabled={submitting}>
          Anuluj
        </button>
      </div>
    </div>
  );
}
