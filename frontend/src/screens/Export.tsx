// ROTA-T021 (arch/T021_spec.md §Wydruk Grafiku): thin client over
// api/routers/export.py -> rota.application.schedule_export (T020,
// unchanged) + the new durable_inputs.save_print_settings wrapper
// (save side only, no new validation -- the server validates the frozen
// field shape). Every problem_code the server can return already has its
// own Polish message server-side; this screen never re-translates or
// shows a raw code.
import { useEffect, useState } from "react";
import {
  RESERVE_SLOT_KEYS,
  SitePrintSettingsIn,
  SitePrintSettingsOut,
  WORK_CODE_KEYS,
  WorkCodeIntervalOut,
  api,
} from "../api/client";

const FROZEN_WORK_CODE_HOURS: Record<string, number> = {
  D1: 12, D2: 4, D3: 24, D4: 2, D5: 24, N1: 12, N2: 16, N3: 24, N4: 24, N5: 24,
};

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function firstOfMonthIso(yearMonth: string): string {
  return `${yearMonth}-01`;
}

function shiftMonth(yearMonth: string, delta: number): string {
  const [year, month] = yearMonth.split("-").map(Number);
  const d = new Date(year, month - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

const MONTH_NAMES_PL = [
  "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
  "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",
];

function monthLabel(yearMonth: string): string {
  const [year, month] = yearMonth.split("-").map(Number);
  return `${MONTH_NAMES_PL[month - 1]} ${year}`;
}

function emptySettings(): SitePrintSettingsIn {
  return {
    company_print_name: "",
    site_print_name: "",
    base_regime: "12h",
    work_code_intervals: Object.fromEntries(WORK_CODE_KEYS.map((k) => [k, null])),
    reserve_hours: Object.fromEntries(RESERVE_SLOT_KEYS.map((k) => [k, null])),
  };
}

function downloadPdf(base64: string, filename: string) {
  const bytes = atob(base64);
  const array = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) array[i] = bytes.charCodeAt(i);
  const blob = new Blob([array], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function SettingsForm({
  initial,
  onSaved,
}: {
  initial: SitePrintSettingsOut | SitePrintSettingsIn;
  onSaved: (settings: SitePrintSettingsIn) => void;
}) {
  const [form, setForm] = useState<SitePrintSettingsIn>(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const siteId = (initial as SitePrintSettingsOut).site_id;

  const setInterval = (code: string, field: keyof WorkCodeIntervalOut, value: string | boolean) => {
    setForm((f) => {
      const current = f.work_code_intervals[code] ?? { start_time: "", end_time: "", end_next_day: false };
      return { ...f, work_code_intervals: { ...f.work_code_intervals, [code]: { ...current, [field]: value } } };
    });
  };

  const clearInterval = (code: string) => {
    setForm((f) => ({ ...f, work_code_intervals: { ...f.work_code_intervals, [code]: null } }));
  };

  const setReserve = (slot: string, value: string) => {
    setForm((f) => ({ ...f, reserve_hours: { ...f.reserve_hours, [slot]: value === "" ? null : Number(value) } }));
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.savePrintSettings(siteId, form);
      onSaved(form);
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="create-panel">
      <h3>Ustawienia wydruku</h3>
      {error && <div className="banner-error">{error}</div>}

      <div className="create-panel-fields" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <label>
          <span className="field-label">Nazwa firmy na wydruku</span>
          <input value={form.company_print_name} onChange={(e) => setForm({ ...form, company_print_name: e.target.value })} />
        </label>
        <label>
          <span className="field-label">Nazwa obiektu na wydruku</span>
          <input value={form.site_print_name} onChange={(e) => setForm({ ...form, site_print_name: e.target.value })} />
        </label>
        <label>
          <span className="field-label">Reżim bazowy</span>
          <select value={form.base_regime} onChange={(e) => setForm({ ...form, base_regime: e.target.value as "12h" | "24h" })}>
            <option value="12h">12h</option>
            <option value="24h">24h</option>
          </select>
        </label>
      </div>

      <p className="field-label" style={{ marginTop: 18, marginBottom: 6 }}>
        Kody zmian (godzina rozpoczęcia/zakończenia, tylko dla używanych kodów)
      </p>
      <div className="matrix-table-wrap">
        <table className="roster-table">
          <thead>
            <tr>
              <th>Kod</th>
              <th>Wymagane godziny</th>
              <th>Start</th>
              <th>Koniec</th>
              <th>Koniec nast. dnia</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {WORK_CODE_KEYS.map((code) => {
              const interval = form.work_code_intervals[code];
              return (
                <tr key={code}>
                  <td>{code}</td>
                  <td>{FROZEN_WORK_CODE_HOURS[code]}h</td>
                  <td>
                    <input
                      type="time"
                      value={interval?.start_time ?? ""}
                      onChange={(e) => setInterval(code, "start_time", e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      type="time"
                      value={interval?.end_time ?? ""}
                      onChange={(e) => setInterval(code, "end_time", e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      style={{ width: "auto" }}
                      checked={interval?.end_next_day ?? false}
                      onChange={(e) => setInterval(code, "end_next_day", e.target.checked)}
                    />
                  </td>
                  <td>
                    {interval && (
                      <button className="btn-ghost" onClick={() => clearInterval(code)}>
                        Wyczyść
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="field-label" style={{ marginTop: 18, marginBottom: 6 }}>
        Rezerwy godzinowe (nieobecności)
      </p>
      <div className="create-panel-fields" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
        {RESERVE_SLOT_KEYS.map((slot) => (
          <label key={slot}>
            <span className="field-label">{slot}</span>
            <input
              type="number"
              min={1}
              value={form.reserve_hours[slot] ?? ""}
              onChange={(e) => setReserve(slot, e.target.value)}
            />
          </label>
        ))}
      </div>

      <div className="create-panel-actions" style={{ marginTop: 18 }}>
        <button className="btn-primary" onClick={save} disabled={saving}>
          {saving ? "Zapisywanie…" : "Zapisz ustawienia"}
        </button>
      </div>
    </div>
  );
}

export default function Export({ siteId }: { siteId: string }) {
  const currentYearMonth = todayIso().slice(0, 7);
  const selectableMonths = [shiftMonth(currentYearMonth, -1), currentYearMonth, shiftMonth(currentYearMonth, 1)];
  const [monthInput, setMonthInput] = useState(currentYearMonth);
  const [periodLabel, setPeriodLabel] = useState(monthLabel(currentYearMonth));
  const [settings, setSettings] = useState<SitePrintSettingsOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingSettings, setEditingSettings] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  const loadSettings = () => {
    setLoading(true);
    api
      .getPrintSettings(siteId)
      .then((s) => {
        setSettings(s);
        setEditingSettings(s === null);
      })
      .finally(() => setLoading(false));
  };

  useEffect(loadSettings, [siteId]);

  const runExport = async () => {
    setExporting(true);
    setResult(null);
    try {
      const monthIso = firstOfMonthIso(monthInput);
      const res = await api.exportSchedule(siteId, monthIso, periodLabel);
      if (res.ok && res.pdf_base64) {
        downloadPdf(res.pdf_base64, `grafik-${siteId}-${monthIso}.pdf`);
        setResult({ ok: true, message: `Gotowe. Wersja dokumentu: ${res.document_revision}.` });
      } else {
        setResult({ ok: false, message: res.message ?? "Nieznany problem eksportu." });
      }
    } catch (e: unknown) {
      setResult({ ok: false, message: String((e as Error).message ?? e) });
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Wydruk Grafiku</h3>
          <p className="panel-hint">Wygeneruj drukowalny PDF grafiku dla wybranego miesiąca.</p>
        </div>
      </div>

      {loading ? (
        <p>Ładowanie…</p>
      ) : editingSettings ? (
        <SettingsForm
          initial={settings ?? { site_id: siteId, ...emptySettings() }}
          onSaved={() => {
            setEditingSettings(false);
            loadSettings();
          }}
        />
      ) : (
        <>
          <div className="panel-title-row">
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="field-label">Miesiąc</span>
              <select
                value={monthInput}
                onChange={(e) => {
                  setMonthInput(e.target.value);
                  setPeriodLabel(monthLabel(e.target.value));
                }}
              >
                {selectableMonths.map((m) => (
                  <option key={m} value={m}>
                    {monthLabel(m)}
                  </option>
                ))}
              </select>
            </label>
            <button className="btn-ghost" onClick={() => setEditingSettings(true)}>
              Ustawienia wydruku
            </button>
          </div>

          <label style={{ display: "block", marginBottom: 16 }}>
            <span className="field-label">Etykieta okresu na wydruku</span>
            <input value={periodLabel} onChange={(e) => setPeriodLabel(e.target.value)} />
          </label>

          {result && <div className={result.ok ? "banner-warning" : "banner-error"}>{result.message}</div>}

          <button className="btn-primary" onClick={runExport} disabled={exporting}>
            {exporting ? "Generowanie…" : "Wygeneruj PDF"}
          </button>
        </>
      )}
    </div>
  );
}
