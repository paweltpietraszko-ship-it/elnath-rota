// ROTA-T021 (arch/T021_spec.md §Decyzje koordynatora): thin client over
// api/routers/decisions.py -> rota.application.memory_read (unchanged,
// read-only). blockers[].condition and unblocking_options.text are already
// ready-made Polish text from rota/planning/decision_guidance.py -- this
// screen never re-translates them.
//
// ROTA-T062: navigation used to be prefix-matched off that same Polish
// text (fragile -- any wording change silently broke the button). Each
// option now carries its own stable target from the backend; this screen
// only renders it.
import { useEffect, useState } from "react";
import { DecisionRequiredOut, RosterRow, api } from "../api/client";

const MONTH_NAMES_PL = [
  "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
  "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",
];

function monthLabel(monthIso: string): string {
  const [year, month] = monthIso.slice(0, 7).split("-").map(Number);
  return `${MONTH_NAMES_PL[month - 1]} ${year}`;
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("pl-PL", { dateStyle: "medium", timeStyle: "short" });
}

function DecisionDetail({
  detail,
  siteId,
  onOpenControlPanel,
}: {
  detail: DecisionRequiredOut;
  siteId: string;
  onOpenControlPanel: (tab: "obsada" | "obiekt", context: { decisionRequiredId: string; month: string }) => void;
}) {
  const context = { decisionRequiredId: detail.decision_required_id, month: detail.month };
  const [rosterEmployees, setRosterEmployees] = useState<RosterRow[]>([]);
  useEffect(() => {
    api.listRoster(siteId).then(setRosterEmployees).catch(() => undefined);
  }, [siteId]);
  // ROTA-T060 (ARCHITECT_RULING, brief section 2.9): a name that can't be
  // resolved falls back to a neutral label, never the raw employee_id.
  const nameFor = (employeeId: string): string =>
    rosterEmployees.find((r) => r.employee_id === employeeId)?.display_name ?? "nieznany pracownik";
  return (
    <div className="panel" style={{ marginTop: 12 }}>
      {/* ROTA-T060 (ARCHITECT_RULING 2026-09-09, brief 2.10): coordinator
          identity has no name-resolution mechanism yet -- the owner-decided
          shape until a dedicated identity Task is neutral "Koordynator",
          never the raw coordinator_id. */}
      <p className="panel-hint">
        Zgłoszono przez Koordynator, {formatDateTime(detail.recorded_at)}.
      </p>

      <div style={{ marginTop: 12 }}>
        <span className="field-label">Blokujące zmiany ({detail.blocking_shift_demands.length})</span>
        <ul style={{ margin: "6px 0 0 0", paddingLeft: 18, fontSize: 13 }}>
          {detail.blocking_shift_demands.map((d, i) => (
            <li key={d.demand_id}>
              Zmiana {i + 1}: {formatDateTime(d.start_datetime)} – {formatDateTime(d.end_datetime)}
            </li>
          ))}
        </ul>
      </div>

      <div style={{ marginTop: 12 }}>
        <span className="field-label">Powody ({detail.blockers.length})</span>
        <ul style={{ margin: "6px 0 0 0", paddingLeft: 18, fontSize: 13 }}>
          {detail.blockers.map((b, i) => (
            <li key={i}>
              {nameFor(b.employee_id)}: {b.condition}
            </li>
          ))}
        </ul>
      </div>

      {detail.load_blocker && (
        <div style={{ marginTop: 12 }}>
          <span className="field-label">Przekroczenie tygodniowego czasu pracy</span>
          <p style={{ fontSize: 13, margin: "6px 0 0 0" }}>
            {nameFor(detail.load_blocker.employee_id)}: {detail.load_blocker.hours}h w tygodniu {formatDateTime(detail.load_blocker.window_start)} –{" "}
            {formatDateTime(detail.load_blocker.window_end)}
          </p>
        </div>
      )}

      <div style={{ marginTop: 12 }}>
        <span className="field-label">Możliwe rozwiązania</span>
        <ul style={{ margin: "6px 0 0 0", paddingLeft: 18, fontSize: 13 }}>
          {detail.unblocking_options.map((option, i) => {
            const target = option.target;
            return (
              <li key={i}>
                {target ? (
                  <button className="roster-name-link" onClick={() => onOpenControlPanel(target, context)}>
                    {option.text}
                  </button>
                ) : (
                  option.text
                )}
              </li>
            );
          })}
        </ul>
      </div>

      {detail.linked_action_ids.length > 0 && (
        <div style={{ marginTop: 12 }}>
          {/* ROTA-T060: action ids have no coordinator-facing representation
              -- the count alone is the safe, useful part; the list of raw
              ids conveyed nothing a coordinator could act on. */}
          <span className="field-label">Powiązane akcje ({detail.linked_action_ids.length})</span>
        </div>
      )}
    </div>
  );
}

export default function Decisions({
  siteId,
  onOpenControlPanel,
}: {
  siteId: string;
  onOpenControlPanel: (tab: "obsada" | "obiekt", context: { decisionRequiredId: string; month: string }) => void;
}) {
  const [months, setMonths] = useState<string[]>([]);
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [detail, setDetail] = useState<DecisionRequiredOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .getDecisionMonths(siteId)
      .then((res) => {
        setMonths(res.months);
        setSelectedMonth(res.months[0] ?? null);
      })
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  }, [siteId]);

  useEffect(() => {
    if (!selectedMonth) {
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    api
      .getDecisionForMonth(siteId, selectedMonth)
      .then(setDetail)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setDetailLoading(false));
  }, [siteId, selectedMonth]);

  return (
    <div className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Decyzje koordynatora</h3>
          <p className="panel-hint">Miesiące, w których planowanie utknęło i wymaga Twojej decyzji.</p>
        </div>
      </div>

      {error && <div className="banner-error">{error}</div>}

      {loading ? (
        <p>Ładowanie…</p>
      ) : months.length === 0 ? (
        <p style={{ color: "var(--ink-faint)" }}>Brak oczekujących decyzji dla tego obiektu.</p>
      ) : (
        <>
          <div className="chip-row">
            {months.map((m) => (
              <button key={m} className={`chip${m === selectedMonth ? " chip-active" : ""}`} onClick={() => setSelectedMonth(m)}>
                {monthLabel(m)}
              </button>
            ))}
          </div>

          {detailLoading ? <p>Ładowanie…</p> : detail && <DecisionDetail detail={detail} siteId={siteId} onOpenControlPanel={onOpenControlPanel} />}
        </>
      )}
    </div>
  );
}
