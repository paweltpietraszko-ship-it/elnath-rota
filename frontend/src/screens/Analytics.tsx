// ROTA-T021 (arch/T021_spec.md §Analityka i bilanse): thin client over
// api/routers/analytics.py -> rota.application.analytics_read (unchanged,
// read-only). No write actions live on this screen.
import { Fragment, useEffect, useMemo, useState } from "react";
import { AnalyticsMonthDataOut, CoordinatorAnalyticsViewOut, EmployeeAnalyticsRowOut, api } from "../api/client";

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

const STATUS_LABEL: Record<EmployeeAnalyticsRowOut["status"], string> = {
  AVAILABLE: "dostępne",
  MONTH_AVAILABLE_QUARTER_UNAVAILABLE: "kwartał niedostępny",
  UNAVAILABLE: "niedostępne",
};

const STATUS_BADGE: Record<EmployeeAnalyticsRowOut["status"], string> = {
  AVAILABLE: "badge-on",
  MONTH_AVAILABLE_QUARTER_UNAVAILABLE: "badge-off",
  UNAVAILABLE: "badge-off",
};

function hoursOrDash(v: number | null | undefined): string {
  return v === null || v === undefined ? "—" : String(v);
}

function QuarterBreakdown({ months }: { months: AnalyticsMonthDataOut[] }) {
  return (
    <table className="roster-table" style={{ marginTop: 8 }}>
      <thead>
        <tr>
          <th>Miesiąc</th>
          <th>Cel (h)</th>
          <th>Cel efektywny (h)</th>
          <th>Zaplanowane (h)</th>
          <th>Zrealizowane (h)</th>
          <th>Bilans miesiąca (h)</th>
          <th>Bilans kwartału (h)</th>
          <th>Nierozliczone przeniesienie (h)</th>
        </tr>
      </thead>
      <tbody>
        {months.map((m) => (
          <tr key={m.month}>
            <td>{monthLabel(m.month.slice(0, 7))}</td>
            <td>{m.target_hours}</td>
            <td>{m.effective_target_hours}</td>
            <td>{m.planned_hours}</td>
            <td>{m.realized_hours}</td>
            <td>{m.month_balance}</td>
            <td>{hoursOrDash(m.quarter_balance)}</td>
            <td>{hoursOrDash(m.unresolved_carryover)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function Analytics({ siteId }: { siteId: string }) {
  const currentYearMonth = useMemo(() => todayIso().slice(0, 7), []);
  const [monthInput, setMonthInput] = useState(currentYearMonth);
  const monthIso = firstOfMonthIso(monthInput);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<CoordinatorAnalyticsViewOut | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    setLoading(true);
    setError(null);
    setExpanded(new Set());
    api
      .getAnalytics(siteId, monthIso)
      .then(setView)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  }, [siteId, monthIso]);

  const toggleExpanded = (employeeId: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(employeeId)) next.delete(employeeId);
      else next.add(employeeId);
      return next;
    });
  };

  const rows = view?.rows ?? [];
  const allWarnings = rows.flatMap((r) => r.warnings.map((w) => ({ employeeId: r.employee_id, displayName: r.display_name, text: w })));

  return (
    <div className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Analityka i bilanse</h3>
          <p className="panel-hint">
            Cele godzinowe, plan i realizacja dla obsady lokalnej ({siteId}). Tabela celowo nie obejmuje wsparcia
            zewnętrznego — inaczej niż liczba osób na Przeglądzie. Bilanse dotyczą godzin ze wszystkich obiektów
            danego pracownika, nie tylko tego obiektu.
          </p>
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="field-label">Miesiąc</span>
          <input type="month" value={monthInput} onChange={(e) => setMonthInput(e.target.value)} />
        </label>
      </div>

      {error && <div className="banner-error">{error}</div>}

      {loading ? (
        <p>Ładowanie…</p>
      ) : (
        <div className="matrix-table-wrap">
          <table className="roster-table">
            <thead>
              <tr>
                <th>Pracownik</th>
                <th>Status</th>
                <th>Cel (h)</th>
                <th>Cel efektywny (h)</th>
                <th>Zaplanowane (h)</th>
                <th>Zrealizowane (h)</th>
                <th>Bilans miesiąca (h)</th>
                <th>Bilans kwartału (h)</th>
                <th>Nierozliczone przeniesienie (h)</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const md = row.month_data;
                const isExpanded = expanded.has(row.employee_id);
                return (
                  <Fragment key={row.employee_id}>
                    <tr>
                      <td>{row.display_name}</td>
                      <td>
                        <span className={`badge-pill ${STATUS_BADGE[row.status]}`}>{STATUS_LABEL[row.status]}</span>
                      </td>
                      <td>{hoursOrDash(md?.target_hours)}</td>
                      <td>{hoursOrDash(md?.effective_target_hours)}</td>
                      <td>{hoursOrDash(md?.planned_hours)}</td>
                      <td>{hoursOrDash(md?.realized_hours)}</td>
                      <td>{hoursOrDash(md?.month_balance)}</td>
                      <td>{hoursOrDash(md?.quarter_balance)}</td>
                      <td>{hoursOrDash(md?.unresolved_carryover)}</td>
                      <td>
                        {row.quarter_months.length > 0 && (
                          <button className="btn-ghost" onClick={() => toggleExpanded(row.employee_id)}>
                            {isExpanded ? "Zwiń kwartał" : "Rozwiń kwartał"}
                          </button>
                        )}
                      </td>
                    </tr>
                    {isExpanded && row.quarter_months.length > 0 && (
                      <tr>
                        <td colSpan={10}>
                          <QuarterBreakdown months={row.quarter_months} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={10} style={{ textAlign: "center", color: "var(--ink-faint)", padding: 20 }}>
                    Brak pracowników lokalnych na obsadzie.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {allWarnings.length > 0 && (
        <div className="banner-warning" data-diag-element="analytics-warnings" style={{ marginTop: 16 }}>
          <strong>Uwaga:</strong>
          <ul>
            {allWarnings.map((w, i) => (
              <li key={i}>
                {w.displayName}: {w.text}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
