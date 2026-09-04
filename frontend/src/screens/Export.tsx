// ROTA-T021 (arch/T021_spec.md §Wydruk Grafiku): thin client over
// api/routers/export.py -> rota.application.schedule_export (T020,
// unchanged). Print settings editing lives on Panel sterowania -> Obiekt
// (see PrintSettings.tsx) per the 2026-08-27 UI audit gate -- this screen
// is purely generate/download. Every problem_code the server can return
// already has its own Polish message server-side; this screen never
// re-translates or shows a raw code.
import { useEffect, useState } from "react";
import { api } from "../api/client";

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

function base64ToBlob(base64: string): Blob {
  const bytes = atob(base64);
  const array = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) array[i] = bytes.charCodeAt(i);
  return new Blob([array], { type: "application/pdf" });
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function Export({
  siteId,
  onOpenPrintSettings,
  workingMonth,
}: {
  siteId: string;
  onOpenPrintSettings: () => void;
  // ROTA-T053: shared Room-level working month (YYYY-MM); Export no longer
  // keeps an independent month/period source (brief §4/§7).
  workingMonth: string;
}) {
  // R3-02 (round-3 audit): the period label has no independent source of
  // truth at all -- it's derived from workingMonth, not a free-text field.
  const periodLabel = monthLabel(workingMonth);
  const [hasSettings, setHasSettings] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);
  // ROTA-T041 OWNER-T041-04/T41-C08: preview and download must read the
  // SAME bytes from the ONE export call already made -- previewUrl/filename
  // are derived from that single response, "Pobierz" never re-fetches.
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewBlob, setPreviewBlob] = useState<Blob | null>(null);
  const [previewFilename, setPreviewFilename] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

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
    // T41-C09: clear any previous preview up front, before the new call
    // resolves -- a failed regeneration must never leave the OLD preview on
    // screen looking like it belongs to this attempt.
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setPreviewBlob(null);
    setPreviewFilename(null);
    try {
      const monthIso = firstOfMonthIso(workingMonth);
      const res = await api.exportSchedule(siteId, monthIso, periodLabel);
      if (res.ok && res.pdf_base64) {
        const blob = base64ToBlob(res.pdf_base64);
        setPreviewBlob(blob);
        setPreviewUrl(URL.createObjectURL(blob));
        setPreviewFilename(`grafik-${siteId}-${monthIso}.pdf`);
        setResult({
          ok: true,
          message: `Gotowe. Wersja dokumentu: ${res.document_revision ? res.document_revision.slice(0, 10) : res.document_revision}.`,
        });
      } else {
        setResult({ ok: false, message: res.message ?? "Nieznany problem eksportu." });
      }
    } catch (e: unknown) {
      setResult({ ok: false, message: String((e as Error).message ?? e) });
    } finally {
      setExporting(false);
    }
  };

  const download = () => {
    if (!previewBlob || !previewFilename) return;
    downloadBlob(previewBlob, previewFilename);
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
            <button className="btn-ghost" onClick={onOpenPrintSettings}>
              Ustawienia wydruku
            </button>
          </div>

          {result && <div className={result.ok ? "banner-warning" : "banner-error"}>{result.message}</div>}

          <div className="create-panel-actions">
            <button className="btn-primary" onClick={runExport} disabled={exporting}>
              {exporting ? "Generowanie…" : "Wygeneruj podgląd PDF"}
            </button>
            {previewUrl && (
              <button className="btn-ghost" data-diag-action="export-download" onClick={download}>
                Pobierz
              </button>
            )}
          </div>

          {previewUrl && (
            <iframe
              title="Podgląd wydruku"
              src={previewUrl}
              data-diag-element="export-preview"
              style={{ width: "100%", height: 480, marginTop: 12, border: "1px solid var(--ink-faint)" }}
            />
          )}
        </>
      )}
    </div>
  );
}
