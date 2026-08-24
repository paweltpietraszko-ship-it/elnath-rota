// ROTA-T031 (tasks/ROTA-T031/brief.md): Planowanie miesiąca. Thin client
// over api/routers/schedule.py -- every write re-fetches the month view
// afterward rather than trusting a locally reconstructed projection.
import { useEffect, useMemo, useState } from "react";
import { api, AssignmentIn, AssignmentOut, MonthViewOut, PlanningResultOut } from "../api/client";

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

function daysInMonth(monthIso: string): string[] {
  const [year, month] = monthIso.split("-").map(Number);
  const count = new Date(year, month, 0).getDate();
  return Array.from({ length: count }, (_, i) => `${monthIso.slice(0, 8)}${String(i + 1).padStart(2, "0")}`);
}

function stripDisplayName(a: AssignmentOut): AssignmentIn {
  const { employee_display_name: _drop, ...rest } = a;
  return rest;
}

function cellLabel(a: AssignmentOut, demandKindByDemandId: Map<string, string | null>): string {
  const kind = a.covers_demand_id ? demandKindByDemandId.get(a.covers_demand_id) : null;
  const base = kind ?? "?";
  return a.role === "TRAINEE" ? `${base}·S` : base;
}

function ScheduleGrid({
  monthIso, assignments, demandKindByDemandId,
}: {
  monthIso: string;
  assignments: AssignmentOut[];
  demandKindByDemandId: Map<string, string | null>;
}) {
  const days = useMemo(() => daysInMonth(monthIso), [monthIso]);
  const employees = useMemo(() => {
    const byId = new Map<string, string>();
    for (const a of assignments) byId.set(a.employee_id, a.employee_display_name);
    return Array.from(byId.entries()).sort((a, b) => a[1].localeCompare(b[1]));
  }, [assignments]);
  const cellsByEmployeeDay = useMemo(() => {
    const map = new Map<string, AssignmentOut[]>();
    for (const a of assignments) {
      const day = a.start_datetime.slice(0, 10);
      const key = `${a.employee_id}|${day}`;
      const list = map.get(key) ?? [];
      list.push(a);
      map.set(key, list);
    }
    return map;
  }, [assignments]);

  if (employees.length === 0) {
    return <p className="panel-hint">Brak zapisanych przypisań w tej wersji.</p>;
  }

  return (
    <div className="matrix-table-wrap">
      <table className="roster-table grid-table">
        <thead>
          <tr>
            <th>Pracownik</th>
            {days.map((d) => (
              <th key={d}>{d.slice(8, 10)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {employees.map(([employeeId, displayName]) => (
            <tr key={employeeId}>
              <td>{displayName}</td>
              {days.map((d) => {
                const cell = cellsByEmployeeDay.get(`${employeeId}|${d}`);
                return (
                  <td key={d} style={{ textAlign: "center", fontVariantNumeric: "tabular-nums" }}>
                    {cell ? cell.map((a) => cellLabel(a, demandKindByDemandId)).join("/") : ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function MonthlyPlanning({ siteId }: { siteId: string }) {
  const currentYearMonth = useMemo(() => todayIso().slice(0, 7), []);
  const selectableMonths = useMemo(
    () => [shiftMonth(currentYearMonth, -1), currentYearMonth, shiftMonth(currentYearMonth, 1)],
    [currentYearMonth],
  );
  const [monthInput, setMonthInput] = useState(currentYearMonth);
  const monthIso = firstOfMonthIso(monthInput);
  const [scheduledMonths, setScheduledMonths] = useState<Set<string>>(new Set());

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<MonthViewOut | null>(null);

  const [planning, setPlanning] = useState(false);
  const [planResult, setPlanResult] = useState<PlanningResultOut | null>(null);
  const [effectiveFromDraft, setEffectiveFromDraft] = useState(monthIso);

  // R1-1 (round-1 audit): resync the PLAN-first date whenever the selected
  // month changes -- it must never silently keep a stale month's date.
  useEffect(() => {
    setEffectiveFromDraft(monthIso);
  }, [monthIso]);

  const [selecting, setSelecting] = useState(false);
  const [ackDeviations, setAckDeviations] = useState<Set<string>>(new Set());
  const [finalizing, setFinalizing] = useState(false);

  const [showReplan, setShowReplan] = useState(false);
  const [replanFrom, setReplanFrom] = useState(todayIso());
  const [showHistory, setShowHistory] = useState(false);
  const [restoring, setRestoring] = useState(false);

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .getMonthView(siteId, monthIso)
      .then((v) => {
        setView(v);
        setAckDeviations(new Set());
      })
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
    api
      .getScheduleMonths(siteId)
      .then((res) => setScheduledMonths(new Set(res.months.map((m) => m.slice(0, 7)))))
      .catch(() => undefined);
  };

  useEffect(() => {
    setPlanResult(null);
    setShowReplan(false);
    setShowHistory(false);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId, monthIso]);

  const demandKindByDemandId = useMemo(() => {
    const map = new Map<string, string | null>();
    for (const d of view?.demands ?? []) map.set(d.demand_id, d.shift_kind);
    return map;
  }, [view]);

  const runPlan = async () => {
    setPlanning(true);
    setError(null);
    try {
      const effectiveFrom = view?.current_version ? null : effectiveFromDraft;
      const result = await api.planMonth(siteId, monthIso, effectiveFrom);
      setPlanResult(result);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setPlanning(false);
    }
  };

  const chooseCandidate = async (candidate: AssignmentOut[]) => {
    setSelecting(true);
    setError(null);
    try {
      await api.selectCandidate(siteId, monthIso, candidate.map(stripDisplayName));
      setPlanResult(null);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSelecting(false);
    }
  };

  const runReplan = async () => {
    setPlanning(true);
    setError(null);
    try {
      const result = await api.replanMonth(siteId, monthIso, replanFrom);
      setPlanResult(result);
      setShowReplan(false);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setPlanning(false);
    }
  };

  const toggleAck = (id: string) => {
    setAckDeviations((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const finalizeCurrentSet = view?.deviations.map((d) => d.deviation_id) ?? [];
  const ackMatchesCurrent =
    finalizeCurrentSet.length === ackDeviations.size && finalizeCurrentSet.every((id) => ackDeviations.has(id));

  const finalize = async () => {
    setFinalizing(true);
    setError(null);
    try {
      await api.finalizeMonth(siteId, monthIso, Array.from(ackDeviations));
      load();
    } catch (e: unknown) {
      const message = String((e as Error).message ?? e);
      // R1-3 (round-1 audit): a rejected finalize means the acknowledged
      // set was stale -- replace the view with a fresh GET and reset the
      // checkboxes so the user can re-confirm the real current set,
      // without a manual reload. load() itself clears the error banner
      // (setError(null) at its top), so the fresh fetch happens first and
      // the error message is set afterward, or it would be wiped.
      try {
        const fresh = await api.getMonthView(siteId, monthIso);
        setView(fresh);
        setAckDeviations(new Set());
      } catch {
        // the original finalize error below is still shown either way
      }
      setError(message);
    } finally {
      setFinalizing(false);
    }
  };

  const restore = async (versionId: string) => {
    setRestoring(true);
    setError(null);
    try {
      await api.restoreVersion(siteId, monthIso, versionId);
      setShowHistory(false);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setRestoring(false);
    }
  };

  const status = view?.current_version?.status ?? null;
  const isFinal = status === "FINAL_NO_DEVIATIONS" || status === "FINAL_WITH_DEVIATIONS";
  const hasAssignments = (view?.assignments.length ?? 0) > 0;
  const decisionRequired = view?.decision_required ?? null;

  return (
    <div className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Planowanie miesiąca</h3>
          <p className="panel-hint">Otwórz miesiąc, uruchom PLAN, wybierz kandydata, sfinalizuj grafik.</p>
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="field-label">Miesiąc</span>
          <select value={monthInput} onChange={(e) => setMonthInput(e.target.value)}>
            {selectableMonths.map((m) => (
              <option key={m} value={m}>
                {monthLabel(m)}
                {scheduledMonths.has(m) ? " (ma grafik)" : ""}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <div className="banner-error">{error}</div>}

      {loading ? (
        <p>Ładowanie…</p>
      ) : decisionRequired ? (
        <div className="banner-error">
          Wymagana decyzja koordynatora — solver nie mógł ukończyć planu bez rozstrzygnięcia. Rozstrzygnięcie będzie
          dostępne na ekranie „Decyzje koordynatora”. Ten ekran nie tworzy siatki, dopóki decyzja nie zostanie podjęta.
        </div>
      ) : (
        <>
          {!view?.current_version && (
            <div className="create-panel" style={{ marginBottom: 14 }}>
              <p>Brak grafiku na ten miesiąc.</p>
              <div className="create-panel-fields" style={{ gridTemplateColumns: "1fr" }}>
                <label>
                  <span className="field-label">Obowiązuje od</span>
                  <input type="date" value={effectiveFromDraft} onChange={(e) => setEffectiveFromDraft(e.target.value)} />
                </label>
              </div>
              <div className="create-panel-actions">
                <button className="btn-primary" data-diag-action="plan-month-first" onClick={runPlan} disabled={planning}>
                  {planning ? "Planowanie…" : "Zaplanuj (PLAN)"}
                </button>
              </div>
            </div>
          )}

          {view?.current_version && (
            <>
              <p className="panel-hint">
                Wersja: {view.current_version.version_id} — status: {view.current_version.status}
                {view.current_version.effective_from ? ` — obowiązuje od ${view.current_version.effective_from}` : ""}
              </p>

              <ScheduleGrid monthIso={monthIso} assignments={view.assignments} demandKindByDemandId={demandKindByDemandId} />

              {!isFinal && !hasAssignments && (
                <p className="panel-hint">Wersja utworzona, ale nikt jeszcze nie został przypisany — uruchom PLAN i wybierz kandydata.</p>
              )}

              {!isFinal && (
                <div className="create-panel-actions" style={{ marginTop: 12 }}>
                  <button className="btn-primary" data-diag-action="plan-month-recompute" onClick={runPlan} disabled={planning}>
                    {planning ? "Planowanie…" : "Przelicz (PLAN)"}
                  </button>
                </div>
              )}

              {isFinal && !showReplan && (
                <div className="create-panel-actions" style={{ marginTop: 12 }}>
                  <button className="btn-ghost" data-diag-action="replan-open" onClick={() => setShowReplan(true)}>
                    REPLAN
                  </button>
                </div>
              )}

              {showReplan && (
                <div className="create-panel" style={{ marginTop: 12 }}>
                  <div className="create-panel-fields" style={{ gridTemplateColumns: "1fr" }}>
                    <label>
                      <span className="field-label">Data odcięcia (REPLAN)</span>
                      <input type="date" value={replanFrom} onChange={(e) => setReplanFrom(e.target.value)} />
                    </label>
                  </div>
                  <div className="create-panel-actions">
                    <button className="btn-primary" data-diag-action="replan-submit" onClick={runReplan} disabled={planning}>
                      {planning ? "Przeliczanie…" : "Uruchom REPLAN"}
                    </button>
                    <button className="btn-ghost" onClick={() => setShowReplan(false)} disabled={planning}>
                      Anuluj
                    </button>
                  </div>
                </div>
              )}

              {view.deviations.length > 0 && (
                <div className="panel" style={{ marginTop: 12 }}>
                  <h3>Odchylenia</h3>
                  {!isFinal && <p className="panel-hint">Zaznacz wszystkie, żeby móc sfinalizować.</p>}
                  <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                    {view.deviations.map((d) => (
                      <li key={d.deviation_id} style={{ padding: "6px 0", display: "flex", alignItems: "center", gap: 8 }}>
                        {!isFinal && (
                          <input
                            type="checkbox"
                            checked={ackDeviations.has(d.deviation_id)}
                            onChange={() => toggleAck(d.deviation_id)}
                            style={{ width: "auto" }}
                          />
                        )}
                        <span className={`badge-pill ${d.acknowledged ? "badge-on" : "badge-off"}`}>{d.category}</span>
                        <span>{d.label}</span>
                        <span style={{ color: "var(--ink-faint)", fontSize: 12 }}>({d.affected_assignment_or_employee})</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {!isFinal && (
                <div className="create-panel-actions" style={{ marginTop: 12 }}>
                  <button
                    className="btn-primary"
                    data-diag-action="finalize-month"
                    onClick={finalize}
                    disabled={finalizing || !ackMatchesCurrent}
                    title={ackMatchesCurrent ? undefined : "Potwierdź dokładnie bieżący zestaw odchyleń"}
                  >
                    {finalizing ? "Finalizowanie…" : "Finalizuj"}
                  </button>
                </div>
              )}

              <div className="create-panel-actions" style={{ marginTop: 12 }}>
                <button className="btn-ghost" data-diag-action="history-toggle" onClick={() => setShowHistory((s) => !s)}>
                  {showHistory ? "Ukryj historię wersji" : "Historia wersji"}
                </button>
              </div>

              {showHistory && (
                <div className="panel" style={{ marginTop: 12 }}>
                  <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                    {view.version_history.map((v) => (
                      <li key={v.version_id} style={{ padding: "6px 0", display: "flex", alignItems: "center", gap: 8 }}>
                        <span>{v.version_id}</span>
                        <span className="badge-pill badge-on">{v.status}</span>
                        {v.version_id !== view.current_version?.version_id && (
                          <button
                            className="btn-ghost"
                            data-diag-action="restore-version"
                            onClick={() => restore(v.version_id)}
                            disabled={restoring}
                          >
                            Przywróć
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}

          {/* R1-2 (round-1 audit): DECISION_REQUIRED has no transient banner
              here -- the persistent view.decision_required block above (which
              survives reload) is the single source of truth, avoiding a
              duplicate message once load() catches up. */}

          {planResult && planResult.status === "TECHNICAL_ERROR" && (
            <div className="banner-error" style={{ marginTop: 12 }}>
              {planResult.error_message ?? "Błąd techniczny solvera."}
            </div>
          )}

          {planResult && planResult.status === "FEASIBLE" && planResult.candidates.length > 0 && (
            <div className="panel" style={{ marginTop: 12 }}>
              <h3>Kandydaci</h3>
              {planResult.candidates.map((candidate, i) => (
                <div key={i} style={{ marginBottom: 16 }}>
                  <p className="panel-hint">Kandydat {i + 1}</p>
                  <ScheduleGrid monthIso={monthIso} assignments={candidate} demandKindByDemandId={demandKindByDemandId} />
                  <div className="create-panel-actions">
                    <button
                      className="btn-primary"
                      data-diag-action="select-candidate"
                      onClick={() => chooseCandidate(candidate)}
                      disabled={selecting}
                    >
                      {selecting ? "Zapisywanie…" : "Wybierz"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
