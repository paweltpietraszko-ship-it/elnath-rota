// ROTA-T021 (arch/T021_spec.md §Wydruk Grafiku): thin client over
// api/routers/export.py -> rota.application.schedule_export (T020,
// unchanged). Print settings editing lives on Panel sterowania -> Obiekt
// (see PrintSettings.tsx) per the 2026-08-27 UI audit gate -- this screen
// is purely generate/download. Every problem_code the server can return
// already has its own Polish message server-side; this screen never
// re-translates or shows a raw code.
import { useEffect, useState } from "react";
import { api } from "../api/client";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function firstOfMonthIso(yearMonth: string): string {
  return `${yearMonth}-01`;
}

const MONTH_NAMES_PL = [
  "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
  "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",
];

function monthLabel(yearMonth: string): string {
  const [year, month] = yearMonth.split("-").map(Number);
  return `${MONTH_NAMES_PL[month - 1]} ${year}`;
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

export default function Export({ siteId, onOpenPrintSettings }: { siteId: string; onOpenPrintSettings: () => void }) {
  const currentYearMonth = todayIso().slice(0, 7);
  const [monthInput, setMonthInput] = useState(currentYearMonth);
  const [periodLabel, setPeriodLabel] = useState(monthLabel(currentYearMonth));
  const [hasSettings, setHasSettings] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .getPrintSettings(siteId)
      .then((s) => setHasSettings(s !== null))
      .finally(() => setLoading(false));
  }, [siteId]);

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
      ) : hasSettings === false ? (
        <div className="banner-warning">
          Brak zapisanych ustawień wydruku dla tego obiektu.{" "}
          <button className="btn-ghost" onClick={onOpenPrintSettings}>
            Skonfiguruj w Panelu sterowania → Obiekt
          </button>
        </div>
      ) : (
        <>
          <div className="panel-title-row">
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="field-label">Miesiąc</span>
              <input
                type="month"
                value={monthInput}
                onChange={(e) => {
                  setMonthInput(e.target.value);
                  setPeriodLabel(monthLabel(e.target.value));
                }}
              />
            </label>
            <button className="btn-ghost" onClick={onOpenPrintSettings}>
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
