// ROTA-T021 (arch/T021_spec.md §Wydruk Grafiku, hard precondition): print
// settings editing lives on Panel sterowania -> Obiekt (spec's stated
// screen ownership), not on Wydruk Grafiku itself -- moved here per the
// 2026-08-27 UI audit gate (OWNER_CORRECTED). Self-contained: fetches its
// own current settings and saves via api/routers/export.py's
// print-settings endpoints.
import { useEffect, useState } from "react";
import { RESERVE_SLOT_KEYS, SitePrintSettingsIn, SitePrintSettingsOut, WORK_CODE_KEYS, WorkCodeIntervalOut, api } from "../api/client";

// ROTA-T056: matches site_repository._EXTRA_CODE_RE (D/N family, integer suffix >= 6).
const EXTRA_CODE_RE = /^[DN]([6-9]|[1-9][0-9]+)$/;

// Same conversion as MonthlyPlanning.tsx's own firstOfMonthIso -- workingMonth
// is "YYYY-MM", the API needs a full "YYYY-MM-01" date.
function firstOfMonthIso(yearMonth: string): string {
  return `${yearMonth}-01`;
}

const FROZEN_WORK_CODE_HOURS: Record<string, number> = {
  D1: 12, D2: 4, D3: 24, D4: 2, D5: 24, N1: 12, N2: 16, N3: 24, N4: 24, N5: 24,
};

function emptySettings(): SitePrintSettingsIn {
  return {
    company_print_name: "",
    site_print_name: "",
    base_regime: "12h",
    work_code_intervals: Object.fromEntries(WORK_CODE_KEYS.map((k) => [k, null])),
    reserve_hours: Object.fromEntries(RESERVE_SLOT_KEYS.map((k) => [k, null])),
    s1_default_interval: null,
  };
}

// Round-15 audit FINDING 1: the GET response (SitePrintSettingsOut) carries
// site_id; the PUT body (SitePrintSettingsIn) does not and rejects extra
// fields (extra="forbid"). TypeScript's structural typing does NOT strip
// site_id from the runtime object just because a variable is annotated as
// the narrower type -- it has to be dropped explicitly here.
function toFormState(s: SitePrintSettingsOut): SitePrintSettingsIn {
  return {
    company_print_name: s.company_print_name, site_print_name: s.site_print_name, base_regime: s.base_regime,
    work_code_intervals: s.work_code_intervals, reserve_hours: s.reserve_hours,
    s1_default_interval: s.s1_default_interval,
  };
}

export default function PrintSettings({ siteId, workingMonth }: { siteId: string; workingMonth: string }) {
  const [form, setForm] = useState<SitePrintSettingsIn | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  // ROTA-T056: monthly D6+/N6+ extra codes -- own load/save cycle, own
  // subresource, independent of the per-site fields above (brief section 6:
  // "PrintSettings nie tworzy drugiego month state" -- workingMonth is
  // Room's, only consumed here).
  const [extraCodes, setExtraCodes] = useState<Record<string, WorkCodeIntervalOut>>({});
  const [extraLoading, setExtraLoading] = useState(true);
  const [extraSaving, setExtraSaving] = useState(false);
  const [extraError, setExtraError] = useState<string | null>(null);
  const [extraSavedAt, setExtraSavedAt] = useState<number | null>(null);
  const [newCode, setNewCode] = useState("");
  const [newStart, setNewStart] = useState("");
  const [newEnd, setNewEnd] = useState("");
  const [newEndNextDay, setNewEndNextDay] = useState(false);
  const [newCodeError, setNewCodeError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .getPrintSettings(siteId)
      .then((s) => setForm(s ? toFormState(s) : emptySettings()))
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  }, [siteId]);

  const monthIso = firstOfMonthIso(workingMonth);

  useEffect(() => {
    setExtraLoading(true);
    setExtraError(null);
    api
      .getMonthlyExtraWorkCodes(siteId, monthIso)
      .then((r) => setExtraCodes(r.codes))
      .catch((e) => setExtraError(String(e.message ?? e)))
      .finally(() => setExtraLoading(false));
  }, [siteId, monthIso]);

  const addExtraCode = () => {
    setNewCodeError(null);
    const code = newCode.trim().toUpperCase();
    if (!EXTRA_CODE_RE.test(code)) {
      setNewCodeError("Kod musi być rodziny D lub N z liczbą >= 6, np. D7 albo N12.");
      return;
    }
    if (extraCodes[code]) {
      setNewCodeError(`Kod ${code} już istnieje w tym miesiącu.`);
      return;
    }
    if (!newStart || !newEnd) {
      setNewCodeError("Podaj godzinę początku i końca.");
      return;
    }
    setExtraCodes((prev) => ({ ...prev, [code]: { start_time: newStart, end_time: newEnd, end_next_day: newEndNextDay } }));
    setNewCode(""); setNewStart(""); setNewEnd(""); setNewEndNextDay(false);
  };

  const removeExtraCode = (code: string) => {
    setExtraCodes((prev) => {
      const next = { ...prev };
      delete next[code];
      return next;
    });
  };

  const saveExtraCodes = async () => {
    setExtraSaving(true);
    setExtraError(null);
    setExtraSavedAt(null);
    try {
      await api.saveMonthlyExtraWorkCodes(siteId, monthIso, extraCodes);
      setExtraSavedAt(Date.now());
    } catch (e: unknown) {
      setExtraError(String((e as Error).message ?? e));
    } finally {
      setExtraSaving(false);
    }
  };

  const setInterval = (code: string, field: keyof WorkCodeIntervalOut, value: string | boolean) => {
    setForm((f) => {
      if (!f) return f;
      const current = f.work_code_intervals[code] ?? { start_time: "", end_time: "", end_next_day: false };
      return { ...f, work_code_intervals: { ...f.work_code_intervals, [code]: { ...current, [field]: value } } };
    });
  };

  const clearInterval = (code: string) => {
    setForm((f) => (f ? { ...f, work_code_intervals: { ...f.work_code_intervals, [code]: null } } : f));
  };

  const setReserve = (slot: string, value: string) => {
    setForm((f) => (f ? { ...f, reserve_hours: { ...f.reserve_hours, [slot]: value === "" ? null : Number(value) } } : f));
  };

  // ROTA-T052: S1 has no fixed duration (brief section 4) -- this is only a
  // default interval the coordinator can reuse in MonthlyPlanning, not a
  // WORK_CODE_KEYS entry.
  const setS1Interval = (field: keyof WorkCodeIntervalOut, value: string | boolean) => {
    setForm((f) => {
      if (!f) return f;
      const current = f.s1_default_interval ?? { start_time: "", end_time: "", end_next_day: false };
      return { ...f, s1_default_interval: { ...current, [field]: value } };
    });
  };

  const clearS1Interval = () => {
    setForm((f) => (f ? { ...f, s1_default_interval: null } : f));
  };

  const save = async () => {
    if (!form) return;
    setSaving(true);
    setError(null);
    setSavedAt(null);
    try {
      await api.savePrintSettings(siteId, form);
      setSavedAt(Date.now());
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSaving(false);
    }
  };

  if (loading || !form) return <p>Ładowanie…</p>;

  return (
    <div className="create-panel">
      <h3>Ustawienia wydruku</h3>
      <p className="panel-hint">Wymagane, żeby wygenerować PDF na ekranie Wydruk Grafiku.</p>
      {error && <div className="banner-error">{error}</div>}
      {savedAt && <div className="banner-warning">Zapisano.</div>}

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
        S1 — szkolenie okresowe (domyślny przedział, pełne godziny, zmienna długość)
      </p>
      <div className="matrix-table-wrap">
        <table className="roster-table">
          <thead>
            <tr>
              <th>Kod</th>
              <th>Start</th>
              <th>Koniec</th>
              <th>Koniec nast. dnia</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>S1</td>
              <td>
                <input
                  type="time"
                  step={3600}
                  value={form.s1_default_interval?.start_time ?? ""}
                  onChange={(e) => setS1Interval("start_time", e.target.value)}
                />
              </td>
              <td>
                <input
                  type="time"
                  step={3600}
                  value={form.s1_default_interval?.end_time ?? ""}
                  onChange={(e) => setS1Interval("end_time", e.target.value)}
                />
              </td>
              <td>
                <input
                  type="checkbox"
                  style={{ width: "auto" }}
                  checked={form.s1_default_interval?.end_next_day ?? false}
                  onChange={(e) => setS1Interval("end_next_day", e.target.checked)}
                />
              </td>
              <td>
                {form.s1_default_interval && (
                  <button className="btn-ghost" onClick={clearS1Interval}>
                    Wyczyść
                  </button>
                )}
              </td>
            </tr>
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

      {/* ROTA-T056: dodatkowe kody D6+/N6+ dla wskazanego miesiąca -- osobna
          sekcja, osobny zapis, niezależna od pól per-obiekt powyżej. */}
      <p className="field-label" style={{ marginTop: 24, marginBottom: 6 }}>
        Dodatkowe kody dla {workingMonth}
      </p>
      <p className="panel-hint">
        Kody D6, D7, N6, N7... o dowolnej długości — do wyboru przy ręcznej korekcie w tym miesiącu (np. na koniec kwartału). D1–D5/N1–N5 zostają bez zmian.
      </p>
      {extraLoading ? (
        <p>Ładowanie…</p>
      ) : (
        <>
          {extraError && <div className="banner-error">{extraError}</div>}
          {extraSavedAt && <div className="banner-warning">Zapisano.</div>}
          <div className="matrix-table-wrap">
            <table className="roster-table">
              <thead>
                <tr>
                  <th>Kod</th>
                  <th>Start</th>
                  <th>Koniec</th>
                  <th>Koniec nast. dnia</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(extraCodes).map(([code, interval]) => (
                  <tr key={code}>
                    <td>{code}</td>
                    <td>{interval.start_time}</td>
                    <td>{interval.end_time}</td>
                    <td>{interval.end_next_day ? "tak" : "nie"}</td>
                    <td>
                      <button className="btn-ghost" onClick={() => removeExtraCode(code)}>
                        Usuń
                      </button>
                    </td>
                  </tr>
                ))}
                <tr>
                  <td>
                    <input placeholder="np. D7" value={newCode} onChange={(e) => setNewCode(e.target.value)} style={{ width: 60 }} />
                  </td>
                  <td>
                    <input type="time" value={newStart} onChange={(e) => setNewStart(e.target.value)} />
                  </td>
                  <td>
                    <input type="time" value={newEnd} onChange={(e) => setNewEnd(e.target.value)} />
                  </td>
                  <td>
                    <input type="checkbox" style={{ width: "auto" }} checked={newEndNextDay} onChange={(e) => setNewEndNextDay(e.target.checked)} />
                  </td>
                  <td>
                    <button className="btn-ghost" onClick={addExtraCode}>
                      Dodaj
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          {newCodeError && <div className="banner-error">{newCodeError}</div>}
          <div className="create-panel-actions" style={{ marginTop: 12 }}>
            <button className="btn-primary" onClick={saveExtraCodes} disabled={extraSaving}>
              {extraSaving ? "Zapisywanie…" : `Zapisz dodatkowe kody dla ${workingMonth}`}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
