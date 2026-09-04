// ROTA-T031 (tasks/ROTA-T031/brief.md): Planowanie miesiąca. Thin client
// over api/routers/schedule.py -- every write re-fetches the month view
// afterward rather than trusting a locally reconstructed projection.
import { useEffect, useMemo, useRef, useState } from "react";
import { api, AssignmentIn, AssignmentOut, MonthViewOut, PlanningResultOut, RosterRow, ScheduleVersionOut } from "../api/client";
import Export from "./Export";
import { todayIso } from "../localDate";

function firstOfMonthIso(yearMonth: string): string {
  return `${yearMonth}-01`;
}

const SCHEDULE_STATUS_LABEL: Record<ScheduleVersionOut["status"], string> = {
  WORKING: "Wersja robocza",
  WORKING_WITH_DEVIATIONS: "Wersja robocza (z odstępstwami)",
  FINAL_NO_DEVIATIONS: "Zatwierdzona",
  FINAL_WITH_DEVIATIONS: "Zatwierdzona (z odstępstwami)",
};

function formatDateTime(iso: string): string {
  // T048 R3: "short" only shows HH:MM -- two versions created in the same
  // minute (e.g. after a quick REPLAN retry) would render identically,
  // defeating the point of showing this instead of the raw version_id.
  // "medium" includes seconds, which actually disambiguates.
  return new Date(iso).toLocaleString("pl-PL", { dateStyle: "medium", timeStyle: "medium" });
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
  // T037 audit finding R1-01: a CANCELLED+NN assignment must not read as an
  // ordinary planned D/N -- operational_code is the ground truth here, not
  // the demand's shift_kind (which still describes the original, now-moot,
  // plan for this slot).
  if (a.operational_code) return a.operational_code;
  // ROTA-T052: S1 is clearly visible in the grid as its own code, never
  // folded into the D/N "?" fallback or the TRAINEE "·S" suffix.
  if (a.role === "PERIODIC_TRAINING") return "S1";
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
  monthIso, assignments, demandKindByDemandId, onSelectAssignment,
}: {
  monthIso: string;
  assignments: AssignmentOut[];
  demandKindByDemandId: Map<string, string | null>;
  onSelectAssignment?: (assignmentId: string) => void;
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
                    {cell?.map((a, i) => (
                      <span key={a.assignment_id}>
                        {i > 0 && "/"}
                        {onSelectAssignment ? (
                          <button
                            className="btn-ghost"
                            style={{ padding: "0 4px", height: "auto", fontSize: "inherit", fontVariantNumeric: "tabular-nums" }}
                            data-diag-action="manual-correction-select-assignment"
                            onClick={() => onSelectAssignment(a.assignment_id)}
                            title="Ręczna korekta tej zmiany"
                          >
                            {cellLabel(a, demandKindByDemandId)}
                            {a.frozen ? "🔒" : ""}
                          </button>
                        ) : (
                          cellLabel(a, demandKindByDemandId)
                        )}
                      </span>
                    ))}
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

// ROTA-T041 OWNER-T041-04: "Ręczna korekta" and "Wydruk Grafiku" are two nav
// shortcuts into this SAME screen, not two screens -- entryMode only picks
// what's shown by default on arrival (a short instruction, or the print
// fragment expanded), it never changes which operations are available.
type EntryMode = "korekta" | "wydruk" | undefined;

export default function MonthlyPlanning({
  siteId, onOpenPrintSettings, entryMode, workingMonth,
}: {
  siteId: string; onOpenPrintSettings: () => void; entryMode?: EntryMode;
  // ROTA-T053: shared Room-level working month (YYYY-MM); no independent
  // month selector on this screen any more.
  workingMonth: string;
}) {
  const monthIso = firstOfMonthIso(workingMonth);
  const days = useMemo(() => daysInMonth(monthIso), [monthIso]);

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

  // ROTA-T054: tracks whether the currently-shown planResult originates
  // from the persisted, unaccepted preview (view.plan_preview) --
  // reconstructed on load/reload/navigate-back rather than a fresh
  // in-session PLAN/REPLAN response. Only gates confirmReplacePreview
  // below; the "Niezatwierdzony wynik PLAN" label/"Odrzuć wynik" render
  // for any FEASIBLE planResult, persisted or not (by the time the
  // coordinator sees it, a successful PLAN/REPLAN has already tried to
  // persist it).
  const isPersistedPreviewRef = useRef(false);
  const [rejectingPreview, setRejectingPreview] = useState(false);

  useEffect(() => {
    if (view?.plan_preview) {
      setPlanResult({
        status: "FEASIBLE",
        candidates: view.plan_preview.candidates,
        decision_payload: null,
        error_message: null,
        warnings: view.plan_preview.warnings,
        optimization_complete: view.plan_preview.optimization_complete,
      });
      // R2-03 audit fix: without this, a "Szukaj dalej" after reload always
      // dispatched to plain PLAN's own retry, even for a REPLAN preview.
      // A-F2 audit fix: operation_kind is now 3-way (plan/replan_narrow/
      // replan_wide) so a reload can also tell REPLAN's narrow vs. wide
      // stage apart -- without restoring lastWideSearch too, "Szukaj
      // dalej" on a reloaded wide-search preview fell back to the narrow
      // retry instead of continuing the wide search.
      setPlanResultSource(view.plan_preview.operation_kind === "plan" ? "plan" : "replan");
      setLastWideSearch(view.plan_preview.operation_kind === "replan_wide");
      isPersistedPreviewRef.current = true;
    } else if (isPersistedPreviewRef.current) {
      // The preview this screen was showing is gone (accepted, rejected,
      // or invalidated elsewhere) -- never keep showing stale candidates.
      setPlanResult(null);
      isPersistedPreviewRef.current = false;
    }
  }, [view?.plan_preview]);

  const rejectPreview = async () => {
    setRejectingPreview(true);
    setError(null);
    try {
      await api.rejectPlanPreview(siteId, monthIso);
      setPlanResult(null);
      isPersistedPreviewRef.current = false;
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setRejectingPreview(false);
    }
  };

  // OWNER decision 4 (brief section 5/6): before replacing an existing
  // preview with a fresh PLAN/REPLAN, the coordinator must be told plainly.
  const confirmReplacePreview = (): boolean =>
    !isPersistedPreviewRef.current
    || window.confirm("Obecny niezatwierdzony wynik PLAN zostanie zastąpiony nowym. Kontynuować?");

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

  // ROTA-T037 (owner ruling 2026-08-28, narrow scope): Reczna korekta lives
  // inline here, not on a separate screen. No dry-run/preview -- a HARD
  // violation never blocks the save, it comes back as a Deviation and is
  // already shown by the existing "Odchylenia" panel below after reload,
  // which is the whole warning mechanism (no separate banner needed).
  const [editingAssignmentId, setEditingAssignmentId] = useState<string | null>(null);
  const [correctionEffectiveFrom, setCorrectionEffectiveFrom] = useState(todayIso());
  const [correctionSaving, setCorrectionSaving] = useState(false);
  const [rosterEmployees, setRosterEmployees] = useState<RosterRow[]>([]);
  const [showPrint, setShowPrint] = useState(entryMode === "wydruk");

  useEffect(() => {
    api.listRoster(siteId).then(setRosterEmployees).catch(() => undefined);
  }, [siteId]);

  // ROTA-T052: manual S1 (PERIODIC_TRAINING) entry. Start/end are prefilled
  // from the site's configured default interval when one exists (brief
  // section 5: "koordynator... może użyć skonfigurowanego przedziału"), but
  // stay freely editable -- S1 has no fixed duration.
  const [showAddS1, setShowAddS1] = useState(false);
  const [s1EmployeeId, setS1EmployeeId] = useState("");
  const [s1Day, setS1Day] = useState(days[0]);
  useEffect(() => {
    setS1Day(days[0]);
  }, [days]);
  const [s1Start, setS1Start] = useState("");
  const [s1End, setS1End] = useState("");
  const [s1EndNextDay, setS1EndNextDay] = useState(false);
  const [s1Saving, setS1Saving] = useState(false);

  useEffect(() => {
    api
      .getPrintSettings(siteId)
      .then((settings) => {
        const interval = settings?.s1_default_interval;
        if (interval) {
          setS1Start(interval.start_time);
          setS1End(interval.end_time);
          setS1EndNextDay(interval.end_next_day);
        }
      })
      .catch(() => undefined);
  }, [siteId]);

  // ROTA-T041 C-FIX-01: assembler warnings embed the raw employee_id
  // (Python repr, e.g. 'uuid') -- resolve it to the roster display_name
  // here rather than in the backend, since the roster this screen already
  // fetches is the single canonical id->name lookup, not a second one.
  const resolveWarningText = (text: string): string => {
    let resolved = text;
    for (const r of rosterEmployees) {
      resolved = resolved.split(`'${r.employee_id}'`).join(r.display_name);
    }
    return resolved;
  };

  // T41-C05/C07: the screen stays mounted across both nav shortcuts (Room
  // renders one MonthlyPlanning for all three entries), so entryMode can
  // change after first mount too -- react to it, don't just read it once.
  useEffect(() => {
    if (entryMode === "wydruk") setShowPrint(true);
  }, [entryMode]);

  const editingAssignment = view?.assignments.find((a) => a.assignment_id === editingAssignmentId) ?? null;

  const runCorrection = async (upsert: AssignmentIn[]) => {
    setCorrectionSaving(true);
    setError(null);
    try {
      await api.applyManualCorrection(siteId, monthIso, correctionEffectiveFrom, upsert);
      setEditingAssignmentId(null);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setCorrectionSaving(false);
    }
  };

  const reassignEmployee = (newEmployeeId: string) => {
    if (!editingAssignment) return;
    runCorrection([{ ...stripDisplayName(editingAssignment), employee_id: newEmployeeId }]);
  };

  // ROTA-T052 (T52-01/T52-02): S1 start/end must land on a full clock hour;
  // the server-side check (schedule_validation.py) is authoritative, this is
  // just an early, friendly rejection before the round-trip.
  const addS1 = async () => {
    if (!view?.current_version || !s1EmployeeId || !s1Start || !s1End) return;
    if (!s1Start.endsWith(":00") || !s1End.endsWith(":00")) {
      setError("Start i koniec S1 muszą być na pełną godzinę.");
      return;
    }
    const startIso = `${s1Day}T${s1Start}:00`;
    const endDay = s1EndNextDay ? new Date(new Date(`${s1Day}T00:00:00`).getTime() + 86400000).toISOString().slice(0, 10) : s1Day;
    const endIso = `${endDay}T${s1End}:00`;
    if (new Date(endIso) <= new Date(startIso)) {
      setError("Koniec S1 musi być po starcie.");
      return;
    }
    setS1Saving(true);
    setError(null);
    try {
      await api.applyManualCorrection(siteId, monthIso, correctionEffectiveFrom, [
        {
          assignment_id: crypto.randomUUID(), schedule_version_id: view.current_version.version_id,
          employee_id: s1EmployeeId, start_datetime: startIso, end_datetime: endIso,
          role: "PERIODIC_TRAINING", state: "PLANNED", frozen: false,
          covers_demand_id: null, mentor_primary_assignment_id: null, operational_code: null,
          work_period_id: null, required_rest_after_hours: null,
        },
      ]);
      setShowAddS1(false);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setS1Saving(false);
    }
  };

  const cancelS1 = () => {
    if (!editingAssignment) return;
    runCorrection([{ ...stripDisplayName(editingAssignment), state: "CANCELLED" }]);
  };

  const toggleFreeze = async () => {
    if (!editingAssignment) return;
    setCorrectionSaving(true);
    setError(null);
    try {
      await api.freezeOrUnfreeze(siteId, monthIso, correctionEffectiveFrom, editingAssignment.assignment_id, !editingAssignment.frozen);
      setEditingAssignmentId(null);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setCorrectionSaving(false);
    }
  };

  const markNotWorked = async () => {
    if (!editingAssignment) return;
    setCorrectionSaving(true);
    setError(null);
    try {
      await api.markNotWorked(siteId, monthIso, correctionEffectiveFrom, editingAssignment.assignment_id);
      setEditingAssignmentId(null);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setCorrectionSaving(false);
    }
  };

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
    if (!confirmReplacePreview()) return;
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
    if (!confirmReplacePreview()) return;
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
    if (!confirmReplacePreview()) return;
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
    if (!confirmReplacePreview()) return;
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
    if (!confirmReplacePreview()) return;
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
      </div>

      {error && <div className="banner-error">{error}</div>}

      {/* 2026-08-26 owner decision: T010 keeps missing target_hours from
          blocking PLAN, but the warning it already produces
          (assembler._assemble_work_balances) was never surfaced anywhere on
          this screen -- the coordinator had no way to know why equity looked
          off. Shown regardless of loading/decisionRequired state since a
          stale current_version's warnings are still relevant context. */}
      {entryMode === "korekta" && (
        <div className="panel-hint" data-diag-element="correction-instruction">
          Kliknij dowolny wpis w grafiku poniżej, aby wykonać ręczną korektę — działa również wtedy, gdy bieżąca
          wersja jest już finalna.
        </div>
      )}

      {!!view?.warnings.length && (
        <div className="banner-warning" data-diag-element="month-warnings">
          <strong>Uwaga:</strong>
          <ul>
            {view.warnings.map((w, i) => (
              <li key={i}>{resolveWarningText(w)}</li>
            ))}
          </ul>
        </div>
      )}

      {/* ROTA-T041 OWNER-T041-04/T41-C07: "Wydruk Grafiku" must show the
          print fragment on THIS screen regardless of whether a schedule
          version exists yet for the month -- printing/exporting is not
          gated on PLAN having run (Export.tsx fetches its own data by
          month). Rendered outside the `view?.current_version` block below,
          which is specifically about the schedule grid/version lifecycle. */}
      {showPrint && (
        <div style={{ marginTop: 12 }}>
          <Export siteId={siteId} onOpenPrintSettings={onOpenPrintSettings} workingMonth={workingMonth} />
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
                Status: {SCHEDULE_STATUS_LABEL[view.current_version.status]}, utworzono {formatDateTime(view.current_version.created_at)}
                {view.current_version.effective_from ? ` — obowiązuje od ${view.current_version.effective_from}` : ""}
              </p>

              <ScheduleGrid
                monthIso={monthIso} assignments={view.assignments} demandKindByDemandId={demandKindByDemandId}
                onSelectAssignment={setEditingAssignmentId}
              />

              <div className="create-panel-actions" style={{ marginTop: 12 }}>
                <button className="btn-ghost" onClick={() => setShowAddS1((v) => !v)}>
                  {showAddS1 ? "Anuluj dodawanie S1" : "Dodaj S1 (szkolenie okresowe)"}
                </button>
              </div>

              {showAddS1 && (
                <div className="panel" style={{ marginTop: 12 }}>
                  <h3>Dodaj S1</h3>
                  <div className="create-panel-fields" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
                    <label>
                      <span className="field-label">Pracownik</span>
                      <select value={s1EmployeeId} onChange={(e) => setS1EmployeeId(e.target.value)}>
                        <option value="">— wybierz —</option>
                        {rosterEmployees.map((r) => (
                          <option key={r.employee_id} value={r.employee_id}>{r.display_name}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      <span className="field-label">Dzień</span>
                      <input
                        type="date" value={s1Day} min={monthIso} max={days[days.length - 1]}
                        onChange={(e) => setS1Day(e.target.value)}
                      />
                    </label>
                    <label>
                      <span className="field-label">Start</span>
                      <input type="time" step={3600} value={s1Start} onChange={(e) => setS1Start(e.target.value)} />
                    </label>
                    <label>
                      <span className="field-label">Koniec</span>
                      <input type="time" step={3600} value={s1End} onChange={(e) => setS1End(e.target.value)} />
                    </label>
                    <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <input
                        type="checkbox" style={{ width: "auto" }}
                        checked={s1EndNextDay} onChange={(e) => setS1EndNextDay(e.target.checked)}
                      />
                      <span className="field-label">Koniec nast. dnia</span>
                    </label>
                  </div>
                  <div className="create-panel-actions">
                    <button className="btn-primary" onClick={addS1} disabled={s1Saving || !s1EmployeeId || !s1Start || !s1End}>
                      {s1Saving ? "Zapisywanie…" : "Zapisz S1"}
                    </button>
                  </div>
                </div>
              )}

              {/* ROTA-T041 OWNER-T041-04/T41-C06: correction must work even
                  when current_version is FINAL -- the existing
                  apply_manual_correction() already creates a new child
                  WORKING and leaves the FINAL parent's snapshot untouched;
                  this screen only had to stop blocking the click. No new
                  correction backend, no FINAL mutation. */}
              {editingAssignment && (
                <div className="panel" style={{ marginTop: 12 }}>
                  <div className="panel-title-row">
                    <h3>Ręczna korekta — {editingAssignment.employee_display_name}, {editingAssignment.start_datetime.slice(0, 10)}</h3>
                    <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span className="field-label">Obowiązuje od</span>
                      <input type="date" value={correctionEffectiveFrom} onChange={(e) => setCorrectionEffectiveFrom(e.target.value)} />
                    </label>
                  </div>
                  <div className="create-panel-actions">
                    <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span className="field-label">Przypisz innej osobie</span>
                      <select
                        value={editingAssignment.employee_id}
                        disabled={correctionSaving}
                        onChange={(e) => reassignEmployee(e.target.value)}
                      >
                        {rosterEmployees.map((r) => (
                          <option key={r.employee_id} value={r.employee_id}>{r.display_name}</option>
                        ))}
                      </select>
                    </label>
                    <button className="btn-ghost" onClick={toggleFreeze} disabled={correctionSaving}>
                      {editingAssignment.frozen ? "Odmroź" : "Zamroź"}
                    </button>
                    {editingAssignment.role === "PRIMARY" && editingAssignment.state === "PLANNED" && (
                      <button className="btn-ghost" onClick={markNotWorked} disabled={correctionSaving}>
                        Nie przepracował (NN)
                      </button>
                    )}
                    {editingAssignment.role === "PERIODIC_TRAINING" && editingAssignment.state !== "CANCELLED" && (
                      <button className="btn-ghost" onClick={cancelS1} disabled={correctionSaving}>
                        Usuń S1
                      </button>
                    )}
                    <button className="btn-ghost" onClick={() => setEditingAssignmentId(null)} disabled={correctionSaving}>
                      Zamknij
                    </button>
                  </div>
                </div>
              )}

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
                <button className="btn-ghost" data-diag-action="print-toggle" onClick={() => setShowPrint((s) => !s)}>
                  {showPrint ? "Ukryj wydruk" : "Wydruk"}
                </button>
              </div>

              {showHistory && (
                <div className="panel" style={{ marginTop: 12 }}>
                  <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                    {view.version_history.map((v) => (
                      <li key={v.version_id} style={{ padding: "6px 0", display: "flex", alignItems: "center", gap: 8 }}>
                        <span className="badge-pill badge-on">{SCHEDULE_STATUS_LABEL[v.status]}, utworzono {formatDateTime(v.created_at)}</span>
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

          {/* ROTA-T054 (T54-07): a preview READ failure is shown separately
              from the current schedule above, which stays untouched. */}
          {view?.plan_preview_error && (
            <div className="banner-error" style={{ marginTop: 12 }}>
              Nie udało się odczytać niezatwierdzonego wyniku PLAN: {view.plan_preview_error}
            </div>
          )}

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
              <div className="panel-title-row">
                <h3>Kandydaci</h3>
                <span className="badge-pill badge-off" data-diag-element="plan-preview-label">
                  Niezatwierdzony wynik PLAN
                </span>
              </div>
              {/* ROTA-T054 (T54-06): a persistence failure never blocks the
                  save/response, but the coordinator must be told plainly
                  that this result is session-only and will disappear. */}
              {planResult.warnings.some((w) => w.startsWith("PLAN_PREVIEW_NOT_PERSISTED")) && (
                <div className="banner-warning" style={{ marginBottom: 12 }}>
                  Ten wynik nie został zapisany trwale — zniknie po odświeżeniu strony lub opuszczeniu ekranu.
                </div>
              )}
              <div className="create-panel-actions" style={{ marginBottom: 12 }}>
                <button
                  className="btn-ghost"
                  data-diag-action="reject-plan-preview"
                  onClick={rejectPreview}
                  disabled={rejectingPreview || selecting}
                >
                  {rejectingPreview ? "Odrzucanie…" : "Odrzuć wynik"}
                </button>
              </div>
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
