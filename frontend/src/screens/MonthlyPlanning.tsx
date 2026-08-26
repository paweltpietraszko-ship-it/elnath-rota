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

function assignmentHours(a: AssignmentOut): number {
  const start = new Date(a.start_datetime).getTime();
  const end = new Date(a.end_datetime).getTime();
  return Math.round((end - start) / (1000 * 60 * 60));
}

// tasks/ROTA-T031/brief.md section 3: paper reference (Grafiki/7442.jpg) has
// an hours summary at the end of each row -- PRIMARY only, non-CANCELLED
// (matches the backend's own monthly-hours convention), TRAINEE excluded.
function totalHours(assignments: AssignmentOut[]): number {
  return assignments
    .filter((a) => a.role === "PRIMARY" && a.state !== "CANCELLED")
    .reduce((sum, a) => sum + assignmentHours(a), 0);
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
  const assignmentsByEmployee = useMemo(() => {
    const map = new Map<string, AssignmentOut[]>();
    for (const a of assignments) {
      const list = map.get(a.employee_id) ?? [];
      list.push(a);
      map.set(a.employee_id, list);
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
            <th>Suma godzin</th>
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
              <td style={{ textAlign: "center", fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>
                {totalHours(assignmentsByEmployee.get(employeeId) ?? [])}h
              </td>
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
  // Integration audit (2026-08-26), point 4: planResult is shared between
  // ordinary PLAN and REPLAN's two steps -- this tracks which family
  // produced the current planResult, so a "Szukaj dalej" on a
  // FEASIBLE+optimization_complete=false result retries the RIGHT
  // operation (plan vs. the correct replan stage) rather than guessing.
  const [planResultSource, setPlanResultSource] = useState<"plan" | "replan">("plan");
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
  const [excluding, setExcluding] = useState(false);

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

  // Integration audit (2026-08-26), point 4/5: a FEASIBLE result whose
  // optimization_complete is False is still shown to the coordinator (not
  // hidden as if incomplete meant unusable) -- they choose "Użyj tego
  // grafiku" (keep it, done) or "Szukaj dalej" (retry the SAME operation
  // with a higher search_attempt, on the SAME current version -- never a
  // new one). planSearchAttempt tracks ordinary PLAN's own attempt count;
  // resets to 0 whenever a fresh, non-retry PLAN is run.
  const [planSearchAttempt, setPlanSearchAttempt] = useState(0);

  const runPlan = async () => {
    setPlanning(true);
    setError(null);
    setPlanSearchAttempt(0);
    try {
      const effectiveFrom = view?.current_version ? null : effectiveFromDraft;
      const result = await api.planMonth(siteId, monthIso, effectiveFrom, 0);
      setPlanResultSource("plan");
      setPlanResult(result);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setPlanning(false);
    }
  };

  const runPlanSearchAgain = async () => {
    const nextAttempt = planSearchAttempt + 1;
    setPlanning(true);
    setError(null);
    try {
      const effectiveFrom = view?.current_version ? null : effectiveFromDraft;
      const result = await api.planMonth(siteId, monthIso, effectiveFrom, nextAttempt);
      setPlanSearchAttempt(nextAttempt);
      setPlanResultSource("plan");
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

  // Owner-corrected two-step REPLAN (2026-08-26): step 1 (narrow) only ever
  // means "found something", "found nothing under ordinary rules yet"
  // (NARROW_SEARCH_EXHAUSTED -- offers "Szukaj szerzej"), or "ran out of
  // time" (SEARCH_INCOMPLETE -- offer to retry the SAME step). lastWideSearch
  // tracks which step a SEARCH_INCOMPLETE retry should repeat.
  const [lastWideSearch, setLastWideSearch] = useState(false);
  // replanSearchAttempt tracks the CURRENT stage's (narrow or wide) attempt
  // count, for both a SEARCH_INCOMPLETE retry and a FEASIBLE+"Szukaj dalej"
  // request -- reset to 0 only when a genuinely fresh replan() (new child
  // version) runs. A retry/­"Szukaj dalej" NEVER calls replan()/runReplan()
  // again -- that would clone another child on top of the one already
  // current (integration audit point 5/6) -- it uses replanRetry/
  // replanWiderSearch instead, which operate on the existing current
  // version.
  const [replanSearchAttempt, setReplanSearchAttempt] = useState(0);

  const runReplan = async () => {
    setPlanning(true);
    setError(null);
    setLastWideSearch(false);
    setReplanSearchAttempt(0);
    try {
      const result = await api.replanMonth(siteId, monthIso, replanFrom);
      setPlanResultSource("replan");
      setPlanResult(result);
      if (result.status !== "NARROW_SEARCH_EXHAUSTED" && result.status !== "SEARCH_INCOMPLETE") setShowReplan(false);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setPlanning(false);
    }
  };

  const runWiderSearch = async () => {
    setPlanning(true);
    setError(null);
    setLastWideSearch(true);
    setReplanSearchAttempt(0);
    try {
      const result = await api.replanWiderSearch(siteId, monthIso, 0);
      setPlanResultSource("replan");
      setPlanResult(result);
      if (result.status !== "SEARCH_INCOMPLETE") setShowReplan(false);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setPlanning(false);
    }
  };

  const runReplanSearchAgain = async () => {
    const nextAttempt = replanSearchAttempt + 1;
    setPlanning(true);
    setError(null);
    try {
      const result = lastWideSearch
        ? await api.replanWiderSearch(siteId, monthIso, nextAttempt)
        : await api.replanRetry(siteId, monthIso, nextAttempt);
      setReplanSearchAttempt(nextAttempt);
      setPlanResultSource("replan");
      setPlanResult(result);
      if (result.status !== "NARROW_SEARCH_EXHAUSTED" && result.status !== "SEARCH_INCOMPLETE") setShowReplan(false);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setPlanning(false);
    }
  };

  const retrySearchIncomplete = () => runReplanSearchAgain();

  // FEASIBLE+optimization_complete=false "Szukaj dalej" dispatches to
  // whichever family (PLAN vs. REPLAN narrow/wide) actually produced the
  // shown candidate -- see planResultSource above.
  const searchAgainForFeasible = () => (planResultSource === "plan" ? runPlanSearchAgain() : runReplanSearchAgain());

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

  const excludeFromHistory = async (versionId: string) => {
    setExcluding(true);
    setError(null);
    try {
      await api.excludeVersionFromHistory(siteId, monthIso, versionId);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setExcluding(false);
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

      {/* 2026-08-26 owner decision: T010 keeps missing target_hours from
          blocking PLAN, but the warning it already produces
          (assembler._assemble_work_balances) was never surfaced anywhere on
          this screen -- the coordinator had no way to know why equity looked
          off. Shown regardless of loading/decisionRequired state since a
          stale current_version's warnings are still relevant context. */}
      {!!view?.warnings.length && (
        <div className="banner-warning" data-diag-element="month-warnings">
          <strong>Uwaga:</strong>
          <ul>
            {view.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

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

              {/* Owner decision 2026-08-26: koordynator ma mieć obie opcje w
                  tym samym miejscu, przed i po finalizacji -- delikatna
                  korekta (PLAN, minimalna zmiana, np. po zgłoszeniu L4) i
                  całościowa (REPLAN, zawsze inny wariant, chroni to co już
                  się wydarzyło). Nie zastępują się nawzajem. */}
              {!showReplan && (
                <div className="create-panel-actions" style={{ marginTop: 12 }}>
                  {!isFinal && (
                    <button className="btn-primary" data-diag-action="plan-month-recompute" onClick={runPlan} disabled={planning}>
                      {planning ? "Planowanie…" : "Przelicz (PLAN)"}
                    </button>
                  )}
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
                        {v.version_id !== view.current_version?.version_id &&
                          v.status !== "FINAL_NO_DEVIATIONS" &&
                          v.status !== "FINAL_WITH_DEVIATIONS" && (
                            <button
                              className="btn-ghost"
                              data-diag-action="exclude-version-from-history"
                              onClick={() => excludeFromHistory(v.version_id)}
                              disabled={excluding}
                            >
                              Usuń
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

          {/* Owner decision 2026-08-26: REPLAN never returns the same
              schedule silently -- this is the plain, exhaustively-proven
              fact that no other HARD-valid arrangement exists at all, even
              using exceptions, not an error. */}
          {planResult && planResult.status === "NO_ALTERNATIVE" && (
            <div className="banner-warning" style={{ marginTop: 12 }}>
              Nie istnieje żaden inny grafik spełniający zasady dla tego miesiąca — obecny układ pozostaje bez zmian.
            </div>
          )}

          {/* Step 1 (narrow) proved no different schedule exists under
              ordinary rules -- never phrased as "no alternative" (only step
              2's exhaustive proof earns that); offers the explicit choice
              the owner specified instead of silently trying exceptions. */}
          {planResult && planResult.status === "NARROW_SEARCH_EXHAUSTED" && (
            <div className="banner-warning" style={{ marginTop: 12 }}>
              <p style={{ margin: 0 }}>
                Nie znaleziono innego grafiku w ramach zwykłych zasad. Sprawdzić możliwości wymagające wyjątków lub
                Twojej decyzji?
              </p>
              <div className="create-panel-actions" style={{ marginTop: 8 }}>
                <button className="btn-ghost" onClick={() => setPlanResult(null)} disabled={planning}>
                  Zostań przy obecnym grafiku
                </button>
                <button className="btn-primary" data-diag-action="replan-wider-search" onClick={runWiderSearch} disabled={planning}>
                  {planning ? "Szukanie…" : "Szukaj szerzej"}
                </button>
              </div>
            </div>
          )}

          {/* Budget ran out before either step could prove anything -- an
              unproven "maybe", never reported as exhausted/no-alternative. */}
          {planResult && planResult.status === "SEARCH_INCOMPLETE" && (
            <div className="banner-warning" style={{ marginTop: 12 }}>
              <p style={{ margin: 0 }}>Wyszukiwanie nie zostało zakończone w wyznaczonym czasie — spróbuj ponownie.</p>
              <div className="create-panel-actions" style={{ marginTop: 8 }}>
                <button className="btn-primary" data-diag-action="replan-retry-incomplete" onClick={retrySearchIncomplete} disabled={planning}>
                  {planning ? "Szukanie…" : "Ponów wyszukiwanie"}
                </button>
              </div>
            </div>
          )}

          {/* Integration audit (2026-08-26), point 4: FEASIBLE never implies
              "this is provably the best possible schedule" -- when the
              solver's shared budget cut a phase short of an optimality
              proof, the coordinator is told and offered the choice to
              search further, on the SAME version, instead of silently
              presenting a possibly-improvable candidate as final. */}
          {/* Round-2 audit (INT-R2-1, HIGH): "Użyj tego grafiku" must go
              through the EXISTING chooseCandidate/select-candidate for the
              shown candidate -- no separate accepted-state, no second, fake
              confirmation. With exactly one candidate (the common case:
              REPLAN narrow/wide, and ordinary PLAN's own single result)
              this banner offers it directly; with several, the per-candidate
              button below is relabeled instead (same chooseCandidate call),
              since one banner button could not pick among them. */}
          {planResult && planResult.status === "FEASIBLE" && planResult.candidates.length === 1 &&
            !planResult.optimization_complete && (
              <div className="banner-warning" style={{ marginTop: 12 }}>
                <p style={{ margin: 0 }}>
                  Znaleziono grafik spełniający zasady, ale czas na dalszą optymalizację się skończył — może istnieć
                  lepszy układ.
                </p>
                <div className="create-panel-actions" style={{ marginTop: 8 }}>
                  <button
                    className="btn-ghost"
                    data-diag-action="accept-incomplete"
                    onClick={() => chooseCandidate(planResult.candidates[0])}
                    disabled={planning || selecting}
                  >
                    {selecting ? "Zapisywanie…" : "Użyj tego grafiku"}
                  </button>
                  <button
                    className="btn-primary"
                    data-diag-action="search-again-incomplete"
                    onClick={searchAgainForFeasible}
                    disabled={planning || selecting}
                  >
                    {planning ? "Szukanie…" : "Szukaj dalej"}
                  </button>
                </div>
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
                      {selecting
                        ? "Zapisywanie…"
                        : planResult.optimization_complete
                          ? "Wybierz"
                          : "Użyj tego grafiku"}
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
