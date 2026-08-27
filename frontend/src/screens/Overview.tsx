// ROTA-T021 (arch/T021_spec.md §Przeglad): thin client over
// api/routers/overview.py, a composition-only endpoint (no dedicated
// backend module for this screen, per spec) over reads already covered
// by other screens (decisions, schedule version, roster).
import { useEffect, useState } from "react";
import { OverviewOut, api } from "../api/client";

function todayYearMonth(): string {
  return new Date().toISOString().slice(0, 7);
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
}: {
  siteId: string;
  onOpenControlPanel: () => void;
  onOpenPlanning: () => void;
  onOpenDecisions: () => void;
}) {
  const [overview, setOverview] = useState<OverviewOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .getOverview(siteId, `${todayYearMonth()}-01`)
      .then(setOverview)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
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
            <button className="btn-ghost" onClick={onOpenDecisions}>
              Rozwiąż
            </button>
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
          <button className="btn-ghost" onClick={onOpenControlPanel}>
            Otwórz panel sterowania
          </button>
        </div>
      </div>
    </div>
  );
}
