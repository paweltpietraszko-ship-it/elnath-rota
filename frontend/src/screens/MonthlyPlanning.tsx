// ROTA-T031 (tasks/ROTA-T031/brief.md): Planowanie miesiąca. Thin client
// over api/routers/schedule.py -- every write re-fetches the month view
// afterward rather than trusting a locally reconstructed projection.
import { useEffect, useMemo, useRef, useState } from "react";
import { api, AssignmentIn, AssignmentOut, ExportLawItemOut, MonthViewOut, PlanningResultOut, RosterRow, ScheduleVersionOut, TECHNICAL_ERROR_MESSAGE, VersionSnapshotOut, WorkCodeIntervalOut } from "../api/client";
import Export from "./Export";

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

  // ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS: a one-time export-ack, separate
  // from ackDeviations/finalize (brief.md section 4 -- never persisted,
  // never a finalize/DECISION_REQUIRED input). exportBlockingLaw is the
  // fresh LAW list the export endpoint just returned; exportAckFingerprints
  // is what the coordinator has checked for THIS one export attempt.
  const [exportBlockingLaw, setExportBlockingLaw] = useState<ExportLawItemOut[]>([]);
  const [exportAckFingerprints, setExportAckFingerprints] = useState<Set<string>>(new Set());
  const toggleExportAck = (fingerprint: string) => {
    setExportAckFingerprints((prev) => {
      const next = new Set(prev);
      if (next.has(fingerprint)) next.delete(fingerprint);
      else next.add(fingerprint);
      return next;
    });
  };
  // brief.md section 8: never keep a stale export-ack/blocking-LAW state
  // around a site/month/current-version change.
  const currentVersionId = view?.current_version?.version_id ?? null;
  useEffect(() => {
    setExportBlockingLaw([]);
    setExportAckFingerprints(new Set());
  }, [siteId, monthIso, currentVersionId]);

  const [showHistory, setShowHistory] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [versionPreview, setVersionPreview] = useState<VersionSnapshotOut | null>(null);
  const [excluding, setExcluding] = useState(false);
  const [deletingCurrent, setDeletingCurrent] = useState(false);

  // ROTA-T037 (owner ruling 2026-08-28, narrow scope): Reczna korekta lives
  // inline here, not on a separate screen. No dry-run/preview -- a HARD
  // violation never blocks the save, it comes back as a Deviation and is
  // already shown by the existing "Odchylenia" panel below after reload,
  // which is the whole warning mechanism (no separate banner needed).
  const [editingAssignmentId, setEditingAssignmentId] = useState<string | null>(null);
  // ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT: effective_from is no longer a
  // client-supplied field -- the backend always computes it itself. For an
  // already-started Assignment, the only allowed action is recording who
  // actually worked it, which requires this mandatory reason.
  const [correctionReason, setCorrectionReason] = useState("");
  const [correctionSaving, setCorrectionSaving] = useState(false);
  const [rosterEmployees, setRosterEmployees] = useState<RosterRow[]>([]);
  const [showPrint, setShowPrint] = useState(entryMode === "wydruk");
  // ROTA-T056: this month's D6+/N6+ extra codes, for offering at PRIMARY
  // manual correction -- defined in PrintSettings, read-only here.
  const [extraCodesForMonth, setExtraCodesForMonth] = useState<Record<string, WorkCodeIntervalOut>>({});

  useEffect(() => {
    api.listRoster(siteId).then(setRosterEmployees).catch(() => undefined);
  }, [siteId]);

  useEffect(() => {
    api.getMonthlyExtraWorkCodes(siteId, monthIso).then((r) => setExtraCodesForMonth(r.codes)).catch(() => undefined);
  }, [siteId, monthIso]);

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
  //
  // ROTA-T055 R3-01 audit fix: the validator's SOFT warning strings (see
  // rota/planning/validator.py) keep a leading "RULE-CODE SOFT: " prefix
  // and, for DAY_ONLY-N-FALLBACK-01, a trailing "(zapotrzebowanie ...,
  // data ..., reguła ...)" technical reference -- both stay in the raw
  // string because many existing tests classify/grep on them, but the
  // demand_id/rule_version_id inside that parenthetical mean nothing to a
  // coordinator and have no display-name lookup the way employee_id does.
  // Architect audit fix (post-Codex-PASS): the first version of this regex
  // dropped the ENTIRE parenthetical, silently losing the operationally
  // important date along with the meaningless ids -- corrected to keep
  // only "data ..." and drop "zapotrzebowanie .../reguła ..." around it.
  const resolveWarningText = (text: string): string => {
    let resolved = text;
    for (const r of rosterEmployees) {
      resolved = resolved.split(`'${r.employee_id}'`).join(r.display_name);
    }
    resolved = resolved.replace(/^[A-Z][A-Z0-9_]*(-[A-Z0-9]+)*\s+SOFT:\s*/, "");
    resolved = resolved.replace(/\(zapotrzebowanie[^,]*,\s*(data [^,]+),\s*reguła[^)]*\)/, "($1)");
    return resolved;
  };

  // T41-C05/C07: the screen stays mounted across both nav shortcuts (Room
  // renders one MonthlyPlanning for all three entries), so entryMode can
  // change after first mount too -- react to it, don't just read it once.
  useEffect(() => {
    if (entryMode === "wydruk") setShowPrint(true);
  }, [entryMode]);

  const editingAssignment = view?.assignments.find((a) => a.assignment_id === editingAssignmentId) ?? null;
  // ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT section 2: same single boundary
  // as the backend (start_datetime <= now) -- purely a UI gate, the backend
  // re-enforces this regardless of what this screen shows/hides.
  const isAssignmentStarted = editingAssignment ? new Date(editingAssignment.start_datetime) <= new Date() : false;

  useEffect(() => {
    setCorrectionReason("");
  }, [editingAssignmentId]);

  const runCorrection = async (upsert: AssignmentIn[], note?: string) => {
    setCorrectionSaving(true);
    setError(null);
    try {
      await api.applyManualCorrection(siteId, monthIso, upsert, note);
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
    runCorrection(
      [{ ...stripDisplayName(editingAssignment), employee_id: newEmployeeId }],
      isAssignmentStarted ? correctionReason : undefined,
    );
  };

  // ROTA-T056 brief section 8: choosing a monthly D6+/N6+ code builds a new
  // real interval anchored on the date of the uniquely covered D/N demand --
  // same pattern addS1 below already uses for end_next_day. covers_demand_id
  // and every other field stay exactly as they are (§3: the code is never
  // stored, only re-derived at export time from the real interval).
  const editingDemand = editingAssignment?.covers_demand_id
    ? (view?.demands.find((d) => d.demand_id === editingAssignment.covers_demand_id) ?? null)
    : null;
  const editingFamily = editingDemand?.shift_kind ?? null;
  const eligibleForExtraCode = editingAssignment?.role === "PRIMARY" && editingAssignment.state !== "CANCELLED" && !editingAssignment.operational_code && editingFamily != null;
  const extraCodeOptions = eligibleForExtraCode ? Object.keys(extraCodesForMonth).filter((c) => c.startsWith(editingFamily as string)).sort() : [];

  const applyExtraCode = (code: string) => {
    if (!editingAssignment || !editingDemand) return;
    const interval = extraCodesForMonth[code];
    if (!interval) return;
    const anchor = editingDemand.start_datetime.slice(0, 10);
    const startIso = `${anchor}T${interval.start_time}:00`;
    // R11-01 fix: local-midnight-plus-86400000-then-toISOString round-trips
    // through UTC, which in a positive-offset zone (e.g. Europe/Warsaw)
    // rolls the calendar date back and silently loses "next day". Date.UTC
    // in and getUTCFullYear/Month/Date out never touches local time, so the
    // +1 is pure calendar arithmetic regardless of the viewer's timezone.
    const [y, m, d] = anchor.split("-").map(Number);
    const endDay = interval.end_next_day ? (() => {
      const next = new Date(Date.UTC(y, m - 1, d + 1));
      return `${next.getUTCFullYear()}-${String(next.getUTCMonth() + 1).padStart(2, "0")}-${String(next.getUTCDate()).padStart(2, "0")}`;
    })() : anchor;
    const endIso = `${endDay}T${interval.end_time}:00`;
    runCorrection([{ ...stripDisplayName(editingAssignment), start_datetime: startIso, end_datetime: endIso }]);
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
      await api.applyManualCorrection(siteId, monthIso, [
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
      await api.freezeOrUnfreeze(siteId, monthIso, editingAssignment.assignment_id, !editingAssignment.frozen);
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
      await api.markNotWorked(siteId, monthIso, editingAssignment.assignment_id);
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

  // R4-02 (architect audit fix): a preview persistence WRITE failure for
  // this exact result leaves the OLD persisted preview in place. An
  // immediate load() right after setPlanResult(result) would then let the
  // reconstruction effect above silently replace this fresh FEASIBLE
  // result -- and its PLAN_PREVIEW_NOT_PERSISTED warning -- with that
  // stale preview. Skip only this one reload; any later real
  // navigation/reload still reflects reality.
  const loadUnlessFreshPreviewUnpersisted = (result: PlanningResultOut) => {
    if (result.status === "FEASIBLE" && result.warnings.some((w) => w.startsWith("PLAN_PREVIEW_NOT_PERSISTED"))) return;
    load();
  };

  useEffect(() => {
    setPlanResult(null);
    setShowHistory(false);
    setVersionPreview(null);
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
      // ROTA-PLAN-UNKNOWN-AS-TECHNICAL-ERROR R3-01 audit fix: this result is
      // fresh, not a reconstruction of the persisted preview -- if the ref
      // was still true from a PRIOR persisted preview, the reload below
      // would otherwise let the "preview is gone" cleanup effect wipe this
      // exact result out (e.g. a non-FEASIBLE SEARCH_INCOMPLETE, which never
      // gets persisted as a preview at all).
      isPersistedPreviewRef.current = false;
      setPlanResult(result);
      loadUnlessFreshPreviewUnpersisted(result);
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
      isPersistedPreviewRef.current = false;
      setPlanResult(result);
      loadUnlessFreshPreviewUnpersisted(result);
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setPlanning(false);
    }
  };

  // ROTA-T057 follow-up (2026-09-07, owner correction): REPLAN (BOARD.md
  // OWNER_RULING point 2) is the pre-acceptance "I don't like this
  // proposal, show me a genuinely different one" tool -- distinct from
  // PLAN's own protective, minimal-change recompute. It never had a
  // reachable button before T057 either (the old one only ever rendered
  // once a current_version already existed, where it always failed).
  // Usable as the very first action (starts a fresh podejscie) or after a
  // PLAN result is already shown (continues accumulating the same
  // podejscie's signature history -- replan() never clears it, only a
  // fresh PLAN or an explicit reject does).
  const runReplanFresh = async () => {
    if (!confirmReplacePreview()) return;
    setPlanning(true);
    setError(null);
    setLastWideSearch(false);
    setReplanSearchAttempt(0);
    try {
      const result = await api.replanMonth(siteId, monthIso, effectiveFromDraft);
      setPlanResultSource("replan");
      isPersistedPreviewRef.current = false;
      setPlanResult(result);
      loadUnlessFreshPreviewUnpersisted(result);
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
  // request -- reset to 0 only when a genuinely fresh runReplanFresh() call
  // (a new podejscie-continuing replan()) runs. A retry/"Szukaj dalej"
  // NEVER calls replan() again -- it uses replanRetry/replanWiderSearch
  // instead, which continue the SAME pre-acceptance podejscie without
  // resetting its accumulated diversity history.
  const [replanSearchAttempt, setReplanSearchAttempt] = useState(0);

  const runWiderSearch = async () => {
    if (!confirmReplacePreview()) return;
    setPlanning(true);
    setError(null);
    setLastWideSearch(true);
    setReplanSearchAttempt(0);
    try {
      const result = await api.replanWiderSearch(siteId, monthIso, 0);
      setPlanResultSource("replan");
      isPersistedPreviewRef.current = false;
      setPlanResult(result);
      loadUnlessFreshPreviewUnpersisted(result);
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
      isPersistedPreviewRef.current = false;
      setPlanResult(result);
      loadUnlessFreshPreviewUnpersisted(result);
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setPlanning(false);
    }
  };

  // ROTA-PLAN-UNKNOWN-AS-TECHNICAL-ERROR: was hard-wired to REPLAN's own
  // retry, which silently mis-routed a PLAN/Przelicz Plan SEARCH_INCOMPLETE
  // (now possible since the backend maps UNKNOWN to it for that family too)
  // -- same planResultSource dispatch searchAgainForFeasible already uses.
  const retrySearchIncomplete = () => (planResultSource === "plan" ? runPlanSearchAgain() : runReplanSearchAgain());

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

  // ROTA-T057 follow-up (2026-09-07, owner finding): restoring the current-
  // version pointer on an already-live month is now refused backend-side
  // (Przelicz Plan is the only lifecycle-aware way to change it) -- for a
  // live month "Przywróć" is replaced by a read-only "Podglad" instead,
  // which never touches current/history.
  const showVersionPreview = async (versionId: string) => {
    setPreviewLoading(true);
    setError(null);
    try {
      const snapshot = await api.getVersionSnapshot(siteId, monthIso, versionId);
      setVersionPreview(snapshot);
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setPreviewLoading(false);
    }
  };

  const deleteCurrentVersion = async () => {
    if (!window.confirm("Ten grafik zostanie usunięty i będzie można zaplanować miesiąc od nowa. Kontynuować?")) return;
    setDeletingCurrent(true);
    setError(null);
    try {
      await api.deleteCurrentVersion(siteId, monthIso);
      setShowHistory(false);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setDeletingCurrent(false);
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
  // ROTA-T057 follow-up (2026-09-07, owner correction): Przelicz Plan/REPLAN
  // visibility branches on whether the grafik's own first shift already
  // started, not on WORKING/FINAL -- an accepted-but-not-yet-live grafik
  // (this month's "próba", per the owner) gets neither: only Usuń (delete
  // it and Plan again) or Korekta reczna apply there.
  const isLive = view?.current_version?.is_live ?? false;
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
          <Export
            siteId={siteId}
            onOpenPrintSettings={onOpenPrintSettings}
            workingMonth={workingMonth}
            currentVersionId={currentVersionId}
            acknowledgedLawFingerprints={Array.from(exportAckFingerprints)}
            onLawBlocked={setExportBlockingLaw}
            onExportSucceeded={() => {
              setExportBlockingLaw([]);
              setExportAckFingerprints(new Set());
            }}
          />
        </div>
      )}

      {loading ? (
        <p>Ładowanie…</p>
      ) : decisionRequired ? (
        <div className="banner-error">
          {/* ROTA-T062 (brief section 4 point 1/T62-03, R1 audit finding):
              this used to be one generic sentence naming "solver" -- a
              technical word T62-03 forbids -- instead of the real,
              evidence-backed actions decision_guidance.py already builds.
              Same one shared guidance text this screen's own THIRD banner
              and Decyzje koordynatora already use; clicking through to act
              on it still lives on Decyzje koordynatora (the only place
              wired to Panel sterowania navigation). */}
          <p style={{ margin: 0 }}>Wymagana decyzja koordynatora — automatyczne planowanie nie ułożyło grafiku bez rozstrzygnięcia:</p>
          <ul style={{ margin: "6px 0 0 0", paddingLeft: 18 }}>
            {decisionRequired.unblocking_options.map((o, i) => (
              <li key={i}>{o.text}</li>
            ))}
          </ul>
          <p style={{ margin: "6px 0 0 0" }}>
            Szczegóły i możliwe działania: ekran „Decyzje koordynatora”. Ten ekran nie tworzy siatki, dopóki decyzja
            nie zostanie podjęta.
          </p>
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
                <button className="btn-ghost" data-diag-action="replan-fresh" onClick={runReplanFresh} disabled={planning}>
                  {planning ? "Planowanie…" : "REPLAN (inny wariant)"}
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
                  </div>
                  {/* ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT section 8: a
                      started service can only have its actually-worked
                      employee recorded, with a mandatory reason -- other
                      actions that mutate a protected field (extra code,
                      Usuń S1, and -- OWNER_CONFIRMED 2026-09-11 -- freeze/
                      unfreeze) are hidden, not just disabled. NN is a
                      separate, pre-existing, inherently retrospective
                      mechanism this guard never touches and stays
                      available. Backend re-enforces the guarded path
                      regardless of what this screen shows (UI is not a
                      security boundary). */}
                  {isAssignmentStarted && (
                    <p className="panel-hint">
                      Ta służba już się rozpoczęła. Można tylko zapisać, kto faktycznie ją wykonał, podając powód
                      {editingAssignment.role === "PRIMARY" && editingAssignment.state === "PLANNED"
                        ? ", albo zaznaczyć, że pracownik nie przepracował (NN)"
                        : ""}
                      {" "}— pozostałe zmiany są niedostępne.
                    </p>
                  )}
                  <div className="create-panel-actions">
                    <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span className="field-label">Przypisz innej osobie</span>
                      <select
                        value={editingAssignment.employee_id}
                        disabled={correctionSaving || (isAssignmentStarted && !correctionReason.trim())}
                        onChange={(e) => reassignEmployee(e.target.value)}
                      >
                        {rosterEmployees.map((r) => (
                          <option key={r.employee_id} value={r.employee_id}>{r.display_name}</option>
                        ))}
                      </select>
                    </label>
                    {isAssignmentStarted && (
                      <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span className="field-label">Powód (wymagany)</span>
                        <input
                          type="text" value={correctionReason} disabled={correctionSaving}
                          onChange={(e) => setCorrectionReason(e.target.value)}
                          placeholder="np. faktycznie służbę wykonał..."
                        />
                      </label>
                    )}
                    {/* OWNER_CONFIRMED 2026-09-11: freeze/unfreeze IS
                        subject to the historical-mutation guard, unlike NN
                        -- the existing cutover already fully protects a
                        started PRIMARY regardless of `frozen`, so there is
                        no product need to allow it after start. */}
                    {!isAssignmentStarted && (
                      <button className="btn-ghost" onClick={toggleFreeze} disabled={correctionSaving}>
                        {editingAssignment.frozen ? "Odmroź" : "Zamroź"}
                      </button>
                    )}
                    {/* ROTA-T056 brief section 8: dodatkowe kody D6+/N6+
                        zdefiniowane dla tego miesiąca -- tylko rodzina
                        zgodna z pokrywanym demandem, tylko dla zwykłego
                        PRIMARY (nie S1/TRAINEE/NN/CANCELLED). */}
                    {!isAssignmentStarted && eligibleForExtraCode && extraCodeOptions.length > 0 && (
                      <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span className="field-label">Zamień na dodatkowy kod</span>
                        <select
                          defaultValue=""
                          disabled={correctionSaving}
                          onChange={(e) => {
                            if (e.target.value) applyExtraCode(e.target.value);
                            e.target.value = "";
                          }}
                        >
                          <option value="" disabled>
                            Wybierz kod…
                          </option>
                          {extraCodeOptions.map((code) => (
                            <option key={code} value={code}>
                              {code}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                    {/* mark_not_worked is also a separate, pre-existing
                        mechanism -- inherently retrospective (you only know
                        a shift was not worked once it should have started),
                        so it stays available regardless of start time. */}
                    {editingAssignment.role === "PRIMARY" && editingAssignment.state === "PLANNED" && (
                      <button className="btn-ghost" onClick={markNotWorked} disabled={correctionSaving}>
                        Nie przepracował (NN)
                      </button>
                    )}
                    {!isAssignmentStarted && editingAssignment.role === "PERIODIC_TRAINING" && editingAssignment.state !== "CANCELLED" && (
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

              {/* ROTA-T057 follow-up (2026-09-07, owner correction): REPLAN
                  is retired the moment anything is accepted for this month
                  (backend now refuses it outright, any status) -- offering
                  it here always failed. Przelicz Plan is offered only once
                  the grafik is live; before that (this month's "próba",
                  per the owner) the only options are Usuń (delete it, plan
                  again) and Korekta reczna. */}
              {!isLive && (
                <p className="panel-hint">
                  Ten grafik jeszcze nie zaczął obowiązywać — Przelicz Plan tu nie działa. Usuń go i zaplanuj miesiąc
                  od nowa, albo popraw punktowo Korektą ręczną.
                </p>
              )}
              <div className="create-panel-actions" style={{ marginTop: 12 }}>
                {isLive && (
                  <button className="btn-primary" data-diag-action="plan-month-recompute" onClick={runPlan} disabled={planning}>
                    {planning ? "Planowanie…" : "Przelicz (PLAN)"}
                  </button>
                )}
                {!isLive && (
                  <button
                    className="btn-ghost"
                    data-diag-action="delete-current-version"
                    onClick={deleteCurrentVersion}
                    disabled={deletingCurrent}
                  >
                    {deletingCurrent ? "Usuwanie…" : "Usuń"}
                  </button>
                )}
              </div>

              {(view.deviations.length > 0 || exportBlockingLaw.length > 0) && (
                <div className="panel" style={{ marginTop: 12 }}>
                  <h3>Odchylenia</h3>
                  {!isFinal && view.deviations.length > 0 && (
                    <p className="panel-hint">Zaznacz wszystkie, żeby móc sfinalizować.</p>
                  )}
                  {view.deviations.length > 0 && (
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
                  )}
                  {/* ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS: fresh, one-time
                      export-ack list -- separate identity (fingerprint,
                      never deviation_id) and separate checkbox state from
                      the finalize list above; visible even when isFinal
                      (brief.md section 7/P11), never persisted, never a
                      finalize input. */}
                  {exportBlockingLaw.length > 0 && (
                    <>
                      <p className="panel-hint" style={{ marginTop: view.deviations.length > 0 ? 12 : 0 }}>
                        Zaznacz, żeby potwierdzić przed wydrukiem, i wygeneruj PDF ponownie.
                      </p>
                      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                        {exportBlockingLaw.map((item) => (
                          <li key={item.fingerprint} style={{ padding: "6px 0", display: "flex", alignItems: "center", gap: 8 }}>
                            <input
                              type="checkbox"
                              checked={exportAckFingerprints.has(item.fingerprint)}
                              onChange={() => toggleExportAck(item.fingerprint)}
                              style={{ width: "auto" }}
                            />
                            <span className="badge-pill badge-off">{item.category}</span>
                            <span>{item.label}</span>
                            <span style={{ color: "var(--ink-faint)", fontSize: 12 }}>({item.affected_assignment_or_employee})</span>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
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
                          isLive ? (
                            <button
                              className="btn-ghost"
                              data-diag-action="preview-version"
                              onClick={() => showVersionPreview(v.version_id)}
                              disabled={previewLoading}
                            >
                              {previewLoading ? "Wczytywanie…" : "Podgląd"}
                            </button>
                          ) : (
                            <button
                              className="btn-ghost"
                              data-diag-action="restore-version"
                              onClick={() => restore(v.version_id)}
                              disabled={restoring}
                            >
                              Przywróć
                            </button>
                          )
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

              {versionPreview && (
                <div className="panel" style={{ marginTop: 12 }}>
                  <div className="panel-title-row">
                    <h3>Podgląd starej wersji</h3>
                    <button className="btn-ghost" onClick={() => setVersionPreview(null)}>
                      Zamknij
                    </button>
                  </div>
                  <p className="panel-hint">
                    Tylko do przeglądania — ta wersja nie jest bieżąca i nie da się jej przywrócić, bo grafik już żyje.
                  </p>
                  <ScheduleGrid
                    monthIso={monthIso}
                    assignments={versionPreview.assignments}
                    demandKindByDemandId={
                      new Map(versionPreview.demands.map((d) => [d.demand_id, d.shift_kind]))
                    }
                  />
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

          {/* ROTA-TECHNICAL-ERROR-RECOVERY-UX (brief.md section 6/A3):
              PlanningResult.error_message for TECHNICAL_ERROR is raw
              solver/exception text -- never rendered. Same frozen surface
              as any other backend/network technical failure (A4); the
              diagnostic package is offered, and "Kontakt ze wsparciem" is
              a disabled mockup per brief.md section 6 (no real channel
              yet). Neither button proposes Korekta ręczna (A5). */}
          {planResult && planResult.status === "TECHNICAL_ERROR" && (
            <div className="banner-error" style={{ marginTop: 12 }}>
              <p>{TECHNICAL_ERROR_MESSAGE}</p>
              <div className="create-panel-actions">
                <button
                  className="btn-ghost"
                  data-diag-action="technical-error-download-diagnostics"
                  onClick={() => api.downloadDiagnostics().catch(() => undefined)}
                >
                  Pobierz pakiet diagnostyczny
                </button>
                <button className="btn-ghost" disabled title="Wsparcie techniczne niedostępne w tej wersji">
                  Kontakt ze wsparciem
                </button>
              </div>
            </div>
          )}

          {/* ROTA-T058 (OWNER_CORRECTED 2026-09-08): a genuinely non-decision
              result -- the automatic solver cannot cover this month without
              giving someone a third consecutive working day, which is HARD
              and gets no automatic exception. Deliberately no "override"/
              "accept anyway" action here (brief section 2.1/T58-04) -- only
              a readable message; recovery is changing staffing/availability
              and planning again. ROTA-T062 (brief section 4 point 6): the
              text itself now comes from the same shared coordinator
              guidance Decyzje koordynatora uses (decision_guidance.py),
              instead of a second, hand-written copy here -- this is
              deliberately information-only (no button): the target
              screens for these suggestions are reachable via "Decyzje
              koordynatora", not from this banner. */}
          {planResult && planResult.status === "THIRD_CONSECUTIVE_SHIFT_BLOCKED" && (
            <div className="banner-warning" style={{ marginTop: 12 }}>
              {planResult.decision_payload?.unblocking_options.map((o) => o.text).join(" ") ??
                "Nie można ułożyć grafiku bez przydzielenia komuś trzeciej służby pod rząd — to niedozwolone. Zmień obsadę lub dostępność i zaplanuj ponownie."}
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
              <p style={{ margin: 0 }}>Program nie zdążył ułożyć grafiku w dostępnym czasie. Możesz ponowić wyszukiwanie.</p>
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
                {/* ROTA-T057 follow-up (2026-09-07): REPLAN's actual entry
                    point -- "I saw PLAN's proposal, I want a genuinely
                    different one" -- only makes sense pre-acceptance;
                    Przelicz Plan's own preview (post-acceptance, same
                    "Kandydaci" panel) never offers it. */}
                {!view?.current_version && (
                  <button
                    className="btn-ghost"
                    data-diag-action="replan-fresh-again"
                    onClick={runReplanFresh}
                    disabled={rejectingPreview || selecting || planning}
                  >
                    {planning ? "Planowanie…" : "Chcę inny wariant (REPLAN)"}
                  </button>
                )}
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
