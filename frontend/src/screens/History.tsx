// ROTA-T021 (arch/T021_spec.md §Historia i audyt): thin client over
// api/routers/history.py -> rota.application.memory_read (unchanged,
// read-only). No Polish presentation strings exist server-side for
// action_kind/rel -- this screen supplies them (spec explicitly says so).
import { Fragment, useEffect, useState } from "react";
import { CoordinatorActionKind, DecisionRecordOut, MaterialActionDetailOut, MaterialActionSummaryOut, api } from "../api/client";

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
};

const REL_LABEL: Record<string, string> = {
  supersedes: "zastępuje",
  corrects: "koryguje",
  rejects: "odrzuca",
};

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("pl-PL", { dateStyle: "medium", timeStyle: "short" });
}

function StateDiff({ label, state }: { label: string; state: Record<string, unknown> | null }) {
  if (!state) return null;
  return (
    <div style={{ marginTop: 6 }}>
      <span className="field-label">{label}</span>
      <ul style={{ margin: "4px 0 0 0", paddingLeft: 18, fontSize: 12.5 }}>
        {Object.entries(state).map(([key, value]) => (
          <li key={key}>
            {key}: {String(value)}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ActionsTab({ siteId }: { siteId: string }) {
  const [actionKindFilter, setActionKindFilter] = useState<CoordinatorActionKind | "">("");
  const [rows, setRows] = useState<MaterialActionSummaryOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<MaterialActionDetailOut | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .getActionHistory(siteId, actionKindFilter || undefined)
      .then(setRows)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  }, [siteId, actionKindFilter]);

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
                    <td>{row.coordinator_id}</td>
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
                            <div style={{ display: "flex", gap: 32 }}>
                              <StateDiff label="Przed" state={detail.before_state} />
                              <StateDiff label="Po" state={detail.after_state} />
                              {detail.responds_to && (
                                <p style={{ fontSize: 12.5, color: "var(--ink-soft)" }}>
                                  Odpowiedź na decyzję koordynatora z {detail.responds_to.month}.
                                </p>
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
                    <td>{d.coordinator_id}</td>
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
