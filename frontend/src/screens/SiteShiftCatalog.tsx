// ROTA-T030 (tasks/ROTA-T030/brief.md): Panel sterowania -> Obiekt. Local
// draft over the whole shift catalog, one atomic PUT via the existing
// req() client -- no direct fetch, no second diagnostic path.
import { useEffect, useState } from "react";
import { api, ShiftRowOut } from "../api/client";

const WEEKDAY_NAMES = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Nd"];
const HOUR_OPTIONS = Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, "0")}:00`);

interface DraftRow {
  key: string;
  kind: "D" | "N";
  start_time: string;
  end_time: string;
  required_primary_count: number;
  active_weekdays: number[];
}

function newKey(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
}

// Mirrors api/routers/site_profile.py's own end_next_day/duration rule
// (end<=start spans into the next day; equal times are a full 24h shift)
// -- display-only preview, the server is still the source of truth.
function durationHours(start: string, end: string): number {
  const startHour = Number(start.slice(0, 2));
  const endHour = Number(end.slice(0, 2));
  let diff = endHour - startHour;
  if (diff <= 0) diff += 24;
  return diff;
}

function catalogKindLabel(hours: number): string {
  if (hours === 12) return "12h";
  if (hours === 24) return "24h";
  return "INNY";
}

function fromServer(rows: ShiftRowOut[]): DraftRow[] {
  return rows.map((r) => ({
    key: newKey(),
    kind: r.kind,
    start_time: r.start_time,
    end_time: r.end_time,
    required_primary_count: r.required_primary_count,
    active_weekdays: r.active_weekdays,
  }));
}

function blankRow(): DraftRow {
  return {
    key: newKey(), kind: "D", start_time: "06:00", end_time: "18:00",
    required_primary_count: 1, active_weekdays: [1, 2, 3, 4, 5, 6, 7],
  };
}

export default function SiteShiftCatalog({ siteId }: { siteId: string }) {
  const [rows, setRows] = useState<DraftRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .getShiftCatalog(siteId)
      .then((res) => setRows(res.shifts.length > 0 ? fromServer(res.shifts) : [blankRow()]))
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  }, [siteId]);

  const updateRow = (key: string, patch: Partial<DraftRow>) => {
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)));
    setSaved(false);
  };

  const toggleWeekday = (key: string, day: number) => {
    setRows((prev) =>
      prev.map((r) => {
        if (r.key !== key) return r;
        const active = r.active_weekdays.includes(day);
        const next = active ? r.active_weekdays.filter((d) => d !== day) : [...r.active_weekdays, day].sort((a, b) => a - b);
        return { ...r, active_weekdays: next };
      }),
    );
    setSaved(false);
  };

  const addRow = () => {
    setRows((prev) => [...prev, blankRow()]);
    setSaved(false);
  };

  const removeRow = (key: string) => {
    if (rows.length <= 1) return;
    if (!window.confirm("Usunąć tę zmianę z katalogu?")) return;
    setRows((prev) => prev.filter((r) => r.key !== key));
    setSaved(false);
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.putShiftCatalog(
        siteId,
        rows.map((r) => ({
          kind: r.kind,
          start_time: r.start_time,
          end_time: r.end_time,
          required_primary_count: r.required_primary_count,
          active_weekdays: r.active_weekdays,
        })),
      );
      setSaved(true);
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p>Ładowanie…</p>;

  return (
    <div className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Katalog zmian</h3>
          <p className="panel-hint">
            Każdy wiersz to jedna zmiana standardowa — rodzaj, godziny, ile osób, które dni tygodnia.
          </p>
        </div>
        <button className="btn-primary" data-diag-action="shift-catalog-add-row" onClick={addRow}>
          + Dodaj zmianę
        </button>
      </div>

      {error && <div className="banner-error">{error}</div>}

      {rows.map((row) => {
        const hours = durationHours(row.start_time, row.end_time);
        return (
          <div key={row.key} className="create-panel" style={{ marginBottom: 14 }}>
            <div className="create-panel-fields" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr" }}>
              <label>
                <span className="field-label">Rodzaj</span>
                <select value={row.kind} onChange={(e) => updateRow(row.key, { kind: e.target.value as "D" | "N" })}>
                  <option value="D">Dniówka</option>
                  <option value="N">Nocka</option>
                </select>
              </label>
              <label>
                <span className="field-label">Początek</span>
                <select value={row.start_time} onChange={(e) => updateRow(row.key, { start_time: e.target.value })}>
                  {HOUR_OPTIONS.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span className="field-label">Koniec</span>
                <select value={row.end_time} onChange={(e) => updateRow(row.key, { end_time: e.target.value })}>
                  {HOUR_OPTIONS.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span className="field-label">Potrzebnych osób</span>
                <input
                  type="number"
                  min={1}
                  value={row.required_primary_count}
                  onChange={(e) => updateRow(row.key, { required_primary_count: Number(e.target.value) })}
                />
              </label>
            </div>

            <div className="chip-row" style={{ marginTop: 10, marginBottom: 10, flexWrap: "wrap" }}>
              {WEEKDAY_NAMES.map((name, i) => {
                const day = i + 1;
                const active = row.active_weekdays.includes(day);
                return (
                  <button
                    key={day}
                    type="button"
                    className={`chip${active ? " chip-active" : ""}`}
                    data-diag-action="shift-catalog-toggle-weekday"
                    onClick={() => toggleWeekday(row.key, day)}
                  >
                    {name}
                  </button>
                );
              })}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 12, color: "var(--ink-faint)" }}>
                {hours}h — {catalogKindLabel(hours)}
              </span>
              <button
                className="btn-ghost"
                data-diag-action="shift-catalog-remove-row"
                onClick={() => removeRow(row.key)}
                disabled={rows.length <= 1}
                title={rows.length <= 1 ? "Ostatnią zmianę popraw przez edycję" : undefined}
              >
                Usuń
              </button>
            </div>
          </div>
        );
      })}

      <div className="create-panel-actions">
        <button className="btn-primary" data-diag-action="shift-catalog-save" onClick={save} disabled={saving}>
          {saving ? "Zapisywanie…" : "Zapisz katalog"}
        </button>
        {saved && <span style={{ color: "var(--sage)", fontSize: 13, marginLeft: 12 }}>Zapisano.</span>}
      </div>
    </div>
  );
}
