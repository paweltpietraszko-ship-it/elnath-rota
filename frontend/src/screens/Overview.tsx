// ROTA-T021 (arch/T021_spec.md §Przeglad): thin client over
// api/routers/overview.py, a composition-only endpoint (no dedicated
// backend module for this screen, per spec) over reads already covered
// by other screens (decisions, schedule version, roster).
import { useEffect, useState } from "react";
import { DecisionRequiredOut, OverviewOut, api } from "../api/client";
import { todayYearMonth } from "../localDate";

const MONTH_NAMES_PL = [
  "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
  "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",
];

function monthLabel(monthIso: string): string {
  const [year, month] = monthIso.slice(0, 7).split("-").map(Number);
  return `${MONTH_NAMES_PL[month - 1]} ${year}`;
}

const VERSION_STATUS_LABEL: Record<NonNullable<OverviewOut["version_status"]>, string> = {
  WORKING: "roboczy",
  WORKING_WITH_DEVIATIONS: "roboczy, z odchyleniami",
  FINAL_NO_DEVIATIONS: "finalny",
  FINAL_WITH_DEVIATIONS: "finalny, z odchyleniami",
};

export default function Overview({
  siteId,
  onOpenControlPanel,
  onOpenPlanning,
  onOpenDecisions,
  onOpenExport,
}: {
  siteId: string;
  onOpenControlPanel: () => void;
  onOpenPlanning: () => void;
  onOpenDecisions: () => void;
  onOpenExport: () => void;
}) {
  const [overview, setOverview] = useState<OverviewOut | null>(null);
  const [decisionPreviews, setDecisionPreviews] = useState<Record<string, DecisionRequiredOut | null>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const o = await api.getOverview(siteId, `${todayYearMonth()}-01`);
        if (cancelled) return;
        setOverview(o);
        // Round-15 audit FINDING 4: spec requires actual decision CONTENT
        // here, not just the month count -- one extra call per pending
        // month (rarely more than a couple at once) for a one-line
        // preview of what's blocking, reusing the same endpoint Decyzje
        // koordynatora already calls per month.
        const details = await Promise.all(o.decision_months.map((m) => api.getDecisionForMonth(siteId, m).catch(() => null)));
        if (cancelled) return;
        setDecisionPreviews(Object.fromEntries(o.decision_months.map((m, i) => [m, details[i]])));
      } catch (e: unknown) {
        if (!cancelled) setError(String((e as Error).message ?? e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [siteId]);

  if (loading) return <div className="panel"><p>Ładowanie…</p></div>;

  return (
    <div className="panel">
      {error && <div className="banner-error">{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16, marginBottom: 24 }}>
        <div className="matrix-table-wrap" style={{ padding: 16 }}>
          <p className="field-label">Oczekujące decyzje</p>
          <p style={{ fontSize: 28, fontWeight: 600, margin: "6px 0" }}>{overview?.decision_months.length ?? 0}</p>
          {!!overview?.decision_months.length && (
            <ul style={{ margin: "0 0 8px 0", paddingLeft: 18, fontSize: 13 }}>
              {overview.decision_months.map((m) => {
                const preview = decisionPreviews[m];
                const summary = preview
                  ? preview.blockers[0]
                    ? `${preview.blockers[0].employee_id}: ${preview.blockers[0].condition}`
                    : `${preview.blocking_shift_demands.length} blokujących zmian`
                  : null;
                return (
                  <li key={m} style={{ marginBottom: 4 }}>
                    <strong>{monthLabel(m)}</strong>
                    {summary && <> — {summary}</>}{" "}
                    <button className="roster-name-link" onClick={onOpenDecisions}>
                      Rozwiąż
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="matrix-table-wrap" style={{ padding: 16 }}>
          <p className="field-label">Wersja grafiku (ten miesiąc)</p>
          <p style={{ fontSize: 20, fontWeight: 600, margin: "6px 0" }}>
            {overview?.version_status ? VERSION_STATUS_LABEL[overview.version_status] : "brak grafiku"}
          </p>
          {overview?.resumable && (
            <button className="btn-ghost" onClick={onOpenPlanning}>
              Wróć do pracy
            </button>
          )}
        </div>

        <div className="matrix-table-wrap" style={{ padding: 16 }}>
          <p className="field-label">Osoby w obsadzie</p>
          <p style={{ fontSize: 28, fontWeight: 600, margin: "6px 0" }}>{overview?.headcount ?? 0}</p>
        </div>
      </div>

      <div>
        <p className="field-label" style={{ marginBottom: 8 }}>
          Szybkie akcje
        </p>
        <div className="chip-row">
          <button className="btn-primary" onClick={onOpenPlanning}>
            Zaplanuj miesiąc
          </button>
          <button className="btn-ghost" onClick={onOpenExport}>
            Wygeneruj PDF
          </button>
          <button className="btn-ghost" onClick={onOpenControlPanel}>
            Otwórz panel sterowania
          </button>
        </div>
      </div>
    </div>
  );
}
