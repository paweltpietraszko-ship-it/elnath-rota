// ROTA-T021 (arch/T021_spec.md §Historia i audyt): thin client over
// api/routers/history.py -> rota.application.memory_read (unchanged,
// read-only). No Polish presentation strings exist server-side for
// action_kind/rel -- this screen supplies them (spec explicitly says so).
import { Fragment, useEffect, useState } from "react";
import { CoordinatorActionKind, DecisionRecordOut, MaterialActionDetailOut, MaterialActionSummaryOut, RosterRow, api } from "../api/client";

const ACTION_KIND_LABEL: Record<CoordinatorActionKind, string> = {
  CONTEXT_CONFIGURATION_SAVED: "Zapisano konfigurację obiektu",
  EXTERNAL_SUPPORT_WINDOW_CHANGED: "Zmieniono okno wsparcia zewnętrznego",
  AVAILABILITY_CHANGED: "Zmieniono dostępność",
  EMPLOYEE_DAY_ONLY_CHANGED: "Zmieniono flagę „tylko dniówka”",
  SITE_MEMBERSHIP_CHANGED: "Zmieniono obsadę",
  TARGET_HOURS_CHANGED: "Zmieniono cel godzinowy",
  CALENDAR_DAY_CHANGED: "Zmieniono dzień w kalendarzu",
  SITE_PROFILE_CHANGED: "Zmieniono profil zmianowy obiektu",
  SITE_ACTIVE_CHANGED: "Zmieniono aktywność obiektu",
  RULE_DECISION_RECORDED: "Zapisano decyzję o regule",
  SCHEDULE_CANDIDATE_SELECTED: "Wybrano wariant grafiku",
  SCHEDULE_REPLAN_CREATED: "Utworzono ponowne planowanie",
  MANUAL_SCHEDULE_CORRECTION: "Ręczna korekta grafiku",
  ASSIGNMENT_FREEZE_CHANGED: "Zmieniono zamrożenie przypisania",
  ASSIGNMENT_NOT_WORKED: "Oznaczono jako niewykonane",
  TRAINING_REALIZED: "Zrealizowano szkolenie",
  SCHEDULE_FINALIZED: "Sfinalizowano grafik",
  SCHEDULE_RESTORED: "Przywrócono wersję grafiku",
  SCHEDULE_VERSION_DELETED: "Usunięto wersję grafiku",
};

const REL_LABEL: Record<string, string> = {
  supersedes: "zastępuje",
  corrects: "koryguje",
  rejects: "odrzuca",
};

const SOURCE_KIND_LABEL: Record<string, string> = {
  CURRENT_STATE: "stan bieżący",
  AVAILABILITY_VERSION: "wersja dostępności",
  DECISION_RECORD: "zapis decyzji",
  SCHEDULE_VERSION: "wersja grafiku",
  CURRENT_SCHEDULE_POINTER: "wskaźnik bieżącego grafiku",
};

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("pl-PL", { dateStyle: "medium", timeStyle: "short" });
}

// Polish labels for before_state/after_state keys -- grepped from every
// before_state/after_state dict literal in rota/application/durable_inputs.py
// (ground truth, not guessed). Anglicism rule applies even to this raw
// diagnostic diff view; an unmapped future key falls back to the raw key
// rather than crashing, but should get its own entry here when noticed.
const STATE_KEY_LABEL: Record<string, string> = {
  active: "aktywne", content: "treść", current_version_id: "id bieżącej wersji", date: "data",
  day_only: "tylko dniówka", decision_id: "id decyzji", deviations: "odchylenia", employee_id: "pracownik",
  holiday: "święto", month: "miesiąc", planning_regime: "reżim planowania",
  predecessor_decision_id: "poprzednia decyzja", predecessor_rule_version_id: "poprzednia wersja reguły",
  regime_replan_required_months: "miesiące wymagające ponownego planowania", rel: "relacja",
  rule_version_id: "wersja reguły", saved: "zapisane", site: "obiekt", site_id: "obiekt",
  site_profile: "profil obiektu", status: "status", target_hours: "cel godzinowy",
  active_weekdays: "aktywne dni tygodnia", availability_id: "id dostępności",
  availability_version_id: "wersja dostępności", catalog_kind: "rodzaj katalogu", end_date: "data końca",
  end_next_day: "koniec nast. dnia", end_time: "godzina końca", kind: "rodzaj", note: "notatka",
  profile_id: "profil", required_primary_count: "wymagana liczba osób", required_rest_hours: "wymagany odpoczynek (h)",
  standard_shifts: "standardowe zmiany", start_date: "data początku", start_time: "godzina początku",
  supersedes_availability_version_id: "zastępuje wersję dostępności",
  // Round-15 audit FINDING 6: nested site_profile/site objects (grepped
  // from rota/application/bootstrap.py's _profile_state/_site_state) were
  // JSON.stringify'd unchanged, still showing raw English keys one level
  // down -- these two dicts plus their own nested fields are the exact
  // repro, added here so the recursive renderer below can translate them.
  day_only_blocks_n: "tylko dniówka blokuje nockę", external_support_enabled: "wsparcie zewnętrzne włączone",
  training_s_enabled: "szkolenie włączone", training_s_weekdays_only: "szkolenie tylko w dni robocze",
  training_s_default_readiness_threshold: "domyślny próg gotowości szkolenia",
  rolling_7d_decision_threshold_hours: "próg decyzyjny 7-dniowy (h)",
};

function stateKeyLabel(key: string): string {
  return STATE_KEY_LABEL[key] ?? key;
}

// T048: translate a leaf VALUE, but only under the specific key it's known
// to belong to -- never a bare string match, or a coordinator's own free
// text (description/source/reason) containing e.g. "ORDINARY" would be
// silently rewritten too.
const STATE_VALUE_LABEL_BY_KEY: Record<string, Record<string, string>> = {
  planning_regime: { ORDINARY: "standardowy" },
};

function stateValueLabel(stateKey: string | undefined, value: string): string {
  return (stateKey && STATE_VALUE_LABEL_BY_KEY[stateKey]?.[value]) ?? value;
}

// ROTA-T060 (ARCHITECT_RULING, brief T60-06): the recursive before/after
// renderer already translates KEYS (STATE_KEY_LABEL above), but was still
// printing the raw technical VALUE under a translated key -- e.g. "id
// bieżącej wersji: SV-<hash>". Every key here names a value that is purely
// a technical identifier with no human-readable form of its own (unlike
// employee_id, which resolves to a real name below); showing a neutral
// placeholder instead is not a data change (brief 2.8: the real value stays
// in before_state/after_state/persistence), only a presentation choice.
const ID_ONLY_STATE_KEYS = new Set([
  "current_version_id", "decision_id", "predecessor_decision_id", "predecessor_rule_version_id",
  "rule_version_id", "site", "site_id", "availability_id", "availability_version_id",
  "supersedes_availability_version_id", "profile_id",
]);
const REDACTED_ID_PLACEHOLDER = "(zapisano)";

// Round-15 audit FINDING 6: recurse into nested objects/arrays and
// translate keys at every level, instead of JSON.stringify-ing a nested
// value opaquely (which left raw English keys visible one level down).
function renderStateValue(value: unknown, stateKey: string | undefined, nameForEmployee: (id: string) => string): JSX.Element | string {
  if (value === null || value === undefined) return "—";
  if (stateKey && ID_ONLY_STATE_KEYS.has(stateKey) && typeof value === "string") return REDACTED_ID_PLACEHOLDER;
  if (stateKey === "employee_id" && typeof value === "string") return nameForEmployee(value);
  if (Array.isArray(value)) {
    if (value.length === 0) return "(brak)";
    return (
      <ul style={{ margin: "2px 0 0 0", paddingLeft: 16 }}>
        {value.map((v, i) => (
          <li key={i}>{renderStateValue(v, stateKey, nameForEmployee)}</li>
        ))}
      </ul>
    );
  }
  if (typeof value === "object") {
    return (
      <ul style={{ margin: "2px 0 0 0", paddingLeft: 16 }}>
        {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
          <li key={k}>
            {stateKeyLabel(k)}: {renderStateValue(v, k, nameForEmployee)}
          </li>
        ))}
      </ul>
    );
  }
  if (typeof value === "string") return stateValueLabel(stateKey, value);
  return String(value);
}

function StateDiff({
  label, state, nameForEmployee,
}: {
  label: string; state: Record<string, unknown> | null; nameForEmployee: (id: string) => string;
}) {
  if (!state) return null;
  return (
    <div style={{ marginTop: 6 }}>
      <span className="field-label">{label}</span>
      <ul style={{ margin: "4px 0 0 0", paddingLeft: 18, fontSize: 12.5 }}>
        {Object.entries(state).map(([key, value]) => (
          <li key={key}>
            {stateKeyLabel(key)}: {renderStateValue(value, key, nameForEmployee)}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ActionsTab({ siteId }: { siteId: string }) {
  const [actionKindFilter, setActionKindFilter] = useState<CoordinatorActionKind | "">("");
  const [recordedFrom, setRecordedFrom] = useState("");
  const [recordedTo, setRecordedTo] = useState("");
  const [rows, setRows] = useState<MaterialActionSummaryOut[]>([]);
  const [rosterEmployees, setRosterEmployees] = useState<RosterRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<MaterialActionDetailOut | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // ROTA-T060 (ARCHITECT_RULING, brief 2.9/T60-06): before/after diffs can
  // name an arbitrary employee_id -- resolve it the same way every other
  // screen does; a name that can't be resolved is a neutral label, never
  // the raw id.
  const nameForEmployee = (employeeId: string): string =>
    rosterEmployees.find((r) => r.employee_id === employeeId)?.display_name ?? "nieznany pracownik";

  useEffect(() => {
    api.listRoster(siteId).then(setRosterEmployees).catch(() => undefined);
  }, [siteId]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .getActionHistory(siteId, {
        actionKind: actionKindFilter || undefined,
        recordedFrom: recordedFrom ? `${recordedFrom}T00:00:00` : undefined,
        recordedTo: recordedTo ? `${recordedTo}T23:59:59` : undefined,
      })
      .then(setRows)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  }, [siteId, actionKindFilter, recordedFrom, recordedTo]);

  const toggleExpanded = (actionId: string) => {
    if (expandedId === actionId) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(actionId);
    setDetail(null);
    setDetailLoading(true);
    api
      .getActionDetail(actionId)
      .then(setDetail)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setDetailLoading(false));
  };

  return (
    <>
      <div className="panel-title-row">
        <div>
          <h3>Akcje koordynatora</h3>
          <p className="panel-hint">Każda konkretna zmiana wprowadzona w programie, od najnowszej.</p>
        </div>
        <div style={{ display: "flex", gap: 16, alignItems: "flex-end", flexWrap: "wrap" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="field-label">Rodzaj akcji</span>
            <select value={actionKindFilter} onChange={(e) => setActionKindFilter(e.target.value as CoordinatorActionKind | "")}>
              <option value="">Wszystkie</option>
              {(Object.keys(ACTION_KIND_LABEL) as CoordinatorActionKind[]).map((kind) => (
                <option key={kind} value={kind}>
                  {ACTION_KIND_LABEL[kind]}
                </option>
              ))}
            </select>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="field-label">Od</span>
            <input type="date" value={recordedFrom} onChange={(e) => setRecordedFrom(e.target.value)} />
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="field-label">Do</span>
            <input type="date" value={recordedTo} onChange={(e) => setRecordedTo(e.target.value)} />
          </label>
        </div>
      </div>

      {error && <div className="banner-error">{error}</div>}

      {loading ? (
        <p>Ładowanie…</p>
      ) : (
        <div className="matrix-table-wrap">
          <table className="roster-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Akcja</th>
                <th>Koordynator</th>
                <th>Miesiąc</th>
                <th>Notatka</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <Fragment key={row.action_id}>
                  <tr>
                    <td>{formatDateTime(row.recorded_at)}</td>
                    <td>{ACTION_KIND_LABEL[row.action_kind]}</td>
                    <td>Koordynator</td>
                    <td>{row.month ?? "—"}</td>
                    <td>{row.note ?? "—"}</td>
                    <td>
                      <button className="btn-ghost" onClick={() => toggleExpanded(row.action_id)}>
                        {expandedId === row.action_id ? "Zwiń" : "Szczegóły"}
                      </button>
                    </td>
                  </tr>
                  {expandedId === row.action_id && (
                    <tr>
                      <td colSpan={6}>
                        {detailLoading ? (
                          <p>Ładowanie…</p>
                        ) : (
                          detail && (
                            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                              <p style={{ fontSize: 12.5, color: "var(--ink-soft)", margin: 0 }}>
                                {/* ROTA-T060: source_id is a raw technical id
                                    (schedule_version_id/availability_version_id/
                                    decision_id depending on source_kind) with no
                                    human-readable form -- the kind label alone
                                    is the safe, useful part. */}
                                Źródło: {SOURCE_KIND_LABEL[detail.source_kind] ?? detail.source_kind}
                              </p>
                              <div style={{ display: "flex", gap: 32 }}>
                                <StateDiff label="Przed" state={detail.before_state} nameForEmployee={nameForEmployee} />
                                <StateDiff label="Po" state={detail.after_state} nameForEmployee={nameForEmployee} />
                              </div>
                              {detail.responds_to && (
                                <div style={{ fontSize: 12.5, color: "var(--ink-soft)" }}>
                                  {/* ROTA-T060: decision_required_id has no
                                      human-readable form; requested_by is a raw
                                      coordinator_id -- neutral "Koordynator"
                                      per the owner-decided identity shape. */}
                                  <p style={{ margin: 0 }}>
                                    Odpowiedź na decyzję koordynatora z miesiąca {detail.responds_to.month}, zgłoszoną przez
                                    Koordynator ({formatDateTime(detail.responds_to.recorded_at)}).
                                  </p>
                                  {detail.responds_to.linked_action_ids.length > 0 && (
                                    <p style={{ margin: "4px 0 0 0" }}>
                                      Powiązane akcje: {detail.responds_to.linked_action_ids.length}
                                    </p>
                                  )}
                                </div>
                              )}
                            </div>
                          )
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", color: "var(--ink-faint)", padding: 20 }}>
                    Brak akcji dla wybranego filtra.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function RulesTab({ siteId }: { siteId: string }) {
  const [history, setHistory] = useState<Record<string, DecisionRecordOut[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .getRuleHistory(siteId)
      .then(setHistory)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  }, [siteId]);

  const ruleIds = Object.keys(history);

  return (
    <>
      <div className="panel-title-row">
        <div>
          <h3>Historia reguł</h3>
          <p className="panel-hint">Pełny łańcuch decyzji dla każdej zapisanej reguły obiektu.</p>
        </div>
      </div>

      {error && <div className="banner-error">{error}</div>}

      {loading ? (
        <p>Ładowanie…</p>
      ) : ruleIds.length === 0 ? (
        <p style={{ color: "var(--ink-faint)" }}>Brak zapisanych reguł dla tego obiektu.</p>
      ) : (
        ruleIds.map((ruleId) => (
          <div key={ruleId} className="matrix-table-wrap" style={{ marginBottom: 20 }}>
            <p className="field-label" style={{ marginBottom: 6 }}>
              Reguła: {ruleId}
            </p>
            <table className="roster-table">
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Koordynator</th>
                  <th>Treść decyzji</th>
                  <th>Obowiązuje od</th>
                  <th>Relacja</th>
                </tr>
              </thead>
              <tbody>
                {history[ruleId].map((d) => (
                  <tr key={d.decision_id}>
                    <td>{formatDateTime(d.recorded_at)}</td>
                    <td>Koordynator</td>
                    <td>{d.statement}</td>
                    <td>{d.effective_from}</td>
                    <td>{d.rel ? REL_LABEL[d.rel] ?? d.rel : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}
    </>
  );
}

export default function History({ siteId }: { siteId: string }) {
  const [tab, setTab] = useState<"akcje" | "reguly">("akcje");

  return (
    <div className="panel">
      <div className="tab-row">
        <button className={`tab-item${tab === "akcje" ? " tab-item-active" : ""}`} onClick={() => setTab("akcje")}>
          Akcje
        </button>
        <button className={`tab-item${tab === "reguly" ? " tab-item-active" : ""}`} onClick={() => setTab("reguly")}>
          Reguły
        </button>
      </div>

      {tab === "akcje" && <ActionsTab siteId={siteId} />}
      {tab === "reguly" && <RulesTab siteId={siteId} />}
    </div>
  );
}
