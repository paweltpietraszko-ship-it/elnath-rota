import { useEffect, useState } from "react";
import { api, AvailabilityRecordOut, EmployeeDetailOut, MatrixCellOut } from "../api/client";

const WEEKDAY_NAMES = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Nd"];
const AVAILABILITY_KIND_LABELS: Record<string, string> = {
  DAY_SHIFT_OFF: "Wolne w dzień",
  UNAVAILABLE_24H: "Ogólna niedostępność",
  LEAVE_PLAN: "Urlop (planowany)",
  LEAVE_GRANTED: "Urlop (przyznany)",
  SICK_LEAVE: "Zwolnienie chorobowe",
};

const isoToday = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

function isActiveToday(c: MatrixCellOut): boolean {
  const today = isoToday();
  return Boolean(c.applies_from && c.applies_to && c.applies_from <= today && c.applies_to >= today);
}

function cellActiveToday(cells: MatrixCellOut[], predicate: (c: MatrixCellOut) => boolean): boolean {
  return cells.some((c) => predicate(c) && isActiveToday(c));
}

function findActiveCell(cells: MatrixCellOut[], predicate: (c: MatrixCellOut) => boolean): MatrixCellOut | undefined {
  return cells.find((c) => predicate(c) && isActiveToday(c));
}

export default function EmployeeDetail({
  siteId,
  employeeId,
  onBack,
  respondsToDecisionRequiredId = null,
  workingMonth,
}: {
  siteId: string;
  siteName: string;
  employeeId: string;
  onBack: () => void;
  // ROTA-T021 UI audit gate (round-15 FINDING 2): set when this screen was
  // opened while resolving a coordinator decision (via Decyzje
  // koordynatora) -- every matrix mutation below already accepts and
  // forwards this so the resulting DecisionRecord links back correctly.
  respondsToDecisionRequiredId?: string | null;
  // ROTA-T053: shared Room-level working month (YYYY-MM); no independent
  // month selector here any more.
  workingMonth: string;
}) {
  const [detail, setDetail] = useState<EmployeeDetailOut | null>(null);
  const [cells, setCells] = useState<MatrixCellOut[]>([]);
  const month = `${workingMonth}-01`;
  const [targetHours, setTargetHoursState] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddAbsence, setShowAddAbsence] = useState(false);
  const [showDayOnlyExceptionForm, setShowDayOnlyExceptionForm] = useState(false);
  const [matrixBusy, setMatrixBusy] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.getEmployeeDetail(employeeId, siteId),
      api.getEmployeeMatrix(employeeId, siteId, month),
      api.getTargetHours(employeeId, month),
    ])
      .then(([d, m, t]) => {
        setDetail(d);
        setCells(m.cells);
        setTargetHoursState(t.target_hours);
      })
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [employeeId, siteId, month]);

  if (loading || !detail) return <p>Ładowanie…</p>;

  const dniowkaBlocked = cellActiveToday(cells, (c) => c.cell === "dniowka");
  const dayOnlyExceptionActive = cellActiveToday(cells, (c) => c.cell === "day_only_exception");
  // Corrected (round-12 audit R12-3): the day_only exception exempts only
  // the base DAY_ONLY-01 block (T021b brief.md section 2 -- "does not
  // weaken any other HARD"). An independent Nocka restriction is
  // AND-composed and still blocks even while the exception is active.
  const explicitNockaRestriction = cellActiveToday(cells, (c) => c.cell === "nocka");
  const nockaBlocked =
    explicitNockaRestriction || (detail.employee.day_only && !dayOnlyExceptionActive);
  const today = isoToday();
  const ogolnaBlocked = detail.availability.some(
    (r) => r.kind === "UNAVAILABLE_24H" && r.active && r.start_date <= today && r.end_date >= today,
  );

  const toggleDayOnly = async () => {
    try {
      await api.updateDayOnly(employeeId, siteId, !detail.employee.day_only);
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    }
  };

  const removeFromRoster = async () => {
    try {
      await api.updateRosterRow(siteId, employeeId, { enabled: false });
      onBack();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    }
  };

  const toggle24h = async () => {
    try {
      await api.updateRosterRow(siteId, employeeId, { can_work_24h: !detail.membership.can_work_24h });
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    }
  };

  // T029 (owner ruling 2026-08-24): the checkbox itself IS the solver
  // instruction -- click toggles it immediately and permanently (no end
  // date), matching how toggleDayOnly/toggle24h above already work. Only
  // Nocka for a day_only employee is a genuine temporary exception (the
  // owner's own example), so it opens a small dated form instead.
  const toggleShiftKind = async (shiftKind: "D" | "N") => {
    const active = findActiveCell(cells, (c) => c.cell === (shiftKind === "D" ? "dniowka" : "nocka"));
    setMatrixBusy(true);
    setError(null);
    try {
      if (active) {
        await api.endMatrixRuleEarly(employeeId, active.rule_id, { site_id: siteId, effective_from: today, responds_to_decision_required_id: respondsToDecisionRequiredId });
      } else {
        await api.createShiftUnavailability(employeeId, { site_id: siteId, shift_kind: shiftKind, effective_from: today, responds_to_decision_required_id: respondsToDecisionRequiredId });
      }
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setMatrixBusy(false);
    }
  };

  const toggleNocka = () => {
    if (!detail.employee.day_only) {
      toggleShiftKind("N");
      return;
    }
    const exceptionCell = findActiveCell(cells, (c) => c.cell === "day_only_exception");
    if (exceptionCell) {
      endDayOnlyException(exceptionCell.rule_id);
    } else {
      setShowDayOnlyExceptionForm(true);
    }
  };

  const endDayOnlyException = async (ruleId: string) => {
    setMatrixBusy(true);
    setError(null);
    try {
      await api.endMatrixRuleEarly(employeeId, ruleId, { site_id: siteId, effective_from: today, responds_to_decision_required_id: respondsToDecisionRequiredId });
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setMatrixBusy(false);
    }
  };

  const toggleWeekday = async (weekday: number) => {
    const active = findActiveCell(cells, (c) => c.cell === "weekday" && c.weekday === weekday);
    setMatrixBusy(true);
    setError(null);
    try {
      if (active) {
        await api.endMatrixRuleEarly(employeeId, active.rule_id, { site_id: siteId, effective_from: today, responds_to_decision_required_id: respondsToDecisionRequiredId });
      } else {
        await api.createWeekdayUnavailability(employeeId, { site_id: siteId, iso_weekday: weekday, effective_from: today, responds_to_decision_required_id: respondsToDecisionRequiredId });
      }
      load();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setMatrixBusy(false);
    }
  };

  return (
    <>
      <div className="employee-detail-header">
        <div>
          <h1 className="brand-font" style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>
            {detail.employee.display_name}
          </h1>
          <button className="room-breadcrumb-back" onClick={onBack}>
            ← Wróć do obsady
          </button>
        </div>
        <button className="btn-ghost" onClick={removeFromRoster}>
          Usuń z obsady
        </button>
      </div>

      {error && <div className="banner-error">{error}</div>}

      <div className="panel">
        <h3>Dane pracownika</h3>
        <div className="field-row">
          <label>Tylko dniówka (day_only)</label>
          <button className={`matrix-box ${detail.employee.day_only ? "matrix-box-on" : "matrix-box-off"}`} onClick={toggleDayOnly}>
            {detail.employee.day_only ? "✓" : "✕"}
          </button>
        </div>
        <div className="field-row">
          <label>Status szkolenia</label>
          <span className="badge-pill badge-off">{detail.membership.readiness_state}</span>
        </div>
      </div>

      <div className="panel">
        <h3>Macierz dostępności — stan dzisiejszy ({today})</h3>
        <p className="panel-hint" style={{ marginBottom: 14 }}>
          Ptaszek = solver może użyć tej osoby w tym wymiarze. Kliknij, żeby od razu, na stałe, zmienić decyzję —
          Nocka dla pracownika „tylko dniówka” to jedyny wyjątek: włączenie jej pyta o termin, bo z założenia jest
          czasowe.
        </p>
        <div className="matrix-table-wrap">
          <table className="matrix-table">
            <thead>
              <tr>
                <th>Ogólna</th>
                <th>Dniówka</th>
                <th>Nocka</th>
                <th>24h</th>
                {WEEKDAY_NAMES.map((w) => (
                  <th key={w}>{w}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <StatusCell blocked={ogolnaBlocked} />
                </td>
                <td>
                  <button
                    className={`matrix-box ${dniowkaBlocked ? "matrix-box-off" : "matrix-box-on"}`}
                    onClick={() => toggleShiftKind("D")}
                    disabled={matrixBusy}
                    title={dniowkaBlocked ? "kliknij, żeby zezwolić na Dniówkę" : "kliknij, żeby zablokować Dniówkę"}
                  >
                    {dniowkaBlocked ? "✕" : "✓"}
                  </button>
                </td>
                <td>
                  <button
                    className={`matrix-box ${nockaBlocked ? "matrix-box-off" : "matrix-box-on"}`}
                    onClick={toggleNocka}
                    disabled={matrixBusy}
                    title={nockaBlocked ? "kliknij, żeby zezwolić na Nockę" : "kliknij, żeby zablokować Nockę"}
                  >
                    {nockaBlocked ? "✕" : "✓"}
                  </button>
                </td>
                <td>
                  <button className={`matrix-box ${detail.membership.can_work_24h ? "matrix-box-on" : "matrix-box-off"}`} onClick={toggle24h}>
                    {detail.membership.can_work_24h ? "✓" : "✕"}
                  </button>
                </td>
                {[1, 2, 3, 4, 5, 6, 7].map((w) => {
                  const blocked = cellActiveToday(cells, (c) => c.cell === "weekday" && c.weekday === w);
                  return (
                    <td key={w}>
                      <button
                        className={`matrix-box ${blocked ? "matrix-box-off" : "matrix-box-on"}`}
                        onClick={() => toggleWeekday(w)}
                        disabled={matrixBusy}
                        title={blocked ? `kliknij, żeby zezwolić w ${WEEKDAY_NAMES[w - 1]}` : `kliknij, żeby zablokować ${WEEKDAY_NAMES[w - 1]}`}
                      >
                        {blocked ? "✕" : "✓"}
                      </button>
                    </td>
                  );
                })}
              </tr>
            </tbody>
          </table>
        </div>
        {showDayOnlyExceptionForm && (
          <DayOnlyExceptionForm
            employeeId={employeeId}
            siteId={siteId}
            respondsToDecisionRequiredId={respondsToDecisionRequiredId}
            onClose={() => setShowDayOnlyExceptionForm(false)}
            onAdded={() => {
              setShowDayOnlyExceptionForm(false);
              load();
            }}
          />
        )}
      </div>

      <div className="panel">
        <div className="panel-title-row">
          <div>
            <h3>Historia ograniczeń</h3>
            <p className="panel-hint">
              Powstają przez kliknięcie ptaszków powyżej. Tu można poprawić datę albo zakończyć wcześniej.
            </p>
          </div>
        </div>
        <RestrictionList cells={cells} employeeId={employeeId} siteId={siteId} onChanged={load} respondsToDecisionRequiredId={respondsToDecisionRequiredId} />
      </div>

      <div className="panel">
        <div className="panel-title-row">
          <div>
            <h3>Nieobecności (w tym Ogólna dostępność)</h3>
            <p className="panel-hint">Urlop, chorobowe i ogólna niedostępność — wszystko w jednym miejscu.</p>
          </div>
          <button className="btn-primary" onClick={() => setShowAddAbsence(true)}>
            + Zgłoś nieobecność
          </button>
        </div>
        {showAddAbsence && (
          <AddAbsenceForm
            employeeId={employeeId}
            siteId={siteId}
            onClose={() => setShowAddAbsence(false)}
            onAdded={() => {
              setShowAddAbsence(false);
              load();
            }}
          />
        )}
        <AbsenceLog records={detail.availability} employeeId={employeeId} siteId={siteId} onChanged={load} />
      </div>

      <div className="panel">
        <h3>Godziny docelowe</h3>
        <TargetHoursEditor
          employeeId={employeeId}
          siteId={siteId}
          month={month}
          value={targetHours}
          onSaved={load}
        />
      </div>
    </>
  );
}

function StatusCell({ blocked }: { blocked: boolean }) {
  return <span className={`matrix-box ${blocked ? "matrix-box-off" : "matrix-box-on"}`}>{blocked ? "✕" : "✓"}</span>;
}

function restrictionLabel(c: MatrixCellOut): string {
  if (c.cell === "dniowka") return "Dniówka";
  if (c.cell === "nocka") return "Nocka";
  if (c.cell === "day_only_exception") return "Wyjątek: czasowa Nocka";
  if (c.cell === "weekday") return WEEKDAY_NAMES[(c.weekday ?? 1) - 1] ?? "Dzień tygodnia";
  return "Inne";
}

function RestrictionList({
  cells,
  employeeId,
  siteId,
  onChanged,
  respondsToDecisionRequiredId,
}: {
  cells: MatrixCellOut[];
  employeeId: string;
  siteId: string;
  onChanged: () => void;
  respondsToDecisionRequiredId: string | null;
}) {
  // round-13 R12-2B: one rule_id (family) can have >1 SiteRuleVersion
  // effective on different days within one queried month (a mid-period
  // correction) -- rule_version_id is the per-row render/selection
  // identity; rule_id (unchanged per version) is still what update/end
  // are called with.
  const [editingVersionId, setEditingVersionId] = useState<string | null>(null);
  if (cells.length === 0) return <p style={{ color: "var(--ink-faint)", fontSize: 13 }}>Brak aktywnych ograniczeń.</p>;

  return (
    <>
      {cells.map((c) =>
        editingVersionId === c.rule_version_id ? (
          <RestrictionEditRow
            key={c.rule_version_id}
            cell={c}
            employeeId={employeeId}
            siteId={siteId}
            respondsToDecisionRequiredId={respondsToDecisionRequiredId}
            onDone={() => {
              setEditingVersionId(null);
              onChanged();
            }}
            onCancel={() => setEditingVersionId(null)}
          />
        ) : (
          <div key={c.rule_version_id} className="absence-log-item">
            <span>
              <strong>{restrictionLabel(c)}</strong> — od {c.effective_from} do {c.effective_to ?? "bez końca"}
            </span>
            <span style={{ display: "flex", gap: 8 }}>
              <button className="btn-ghost" onClick={() => setEditingVersionId(c.rule_version_id)}>
                Edytuj / zakończ
              </button>
            </span>
          </div>
        ),
      )}
    </>
  );
}

function RestrictionEditRow({
  cell,
  employeeId,
  siteId,
  onDone,
  onCancel,
  respondsToDecisionRequiredId,
}: {
  cell: MatrixCellOut;
  employeeId: string;
  siteId: string;
  onDone: () => void;
  onCancel: () => void;
  respondsToDecisionRequiredId: string | null;
}) {
  const [from, setFrom] = useState(cell.effective_from);
  const [to, setTo] = useState(cell.effective_to ?? "");
  const [endDate, setEndDate] = useState(cell.effective_from > isoToday() ? cell.effective_from : isoToday());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const saveDates = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await api.updateMatrixRule(employeeId, cell.rule_id, { site_id: siteId, effective_from: from, effective_to: to || null, responds_to_decision_required_id: respondsToDecisionRequiredId });
      onDone();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  };

  const endEarly = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await api.endMatrixRuleEarly(employeeId, cell.rule_id, { site_id: siteId, effective_from: endDate, responds_to_decision_required_id: respondsToDecisionRequiredId });
      onDone();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="create-panel" style={{ marginBottom: 10 }}>
      <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>{restrictionLabel(cell)}</p>
      {error && <div className="banner-error">{error}</div>}
      <div className="create-panel-fields" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <label>
          <span className="field-label">Od</span>
          <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label>
          <span className="field-label">Do (puste = bezterminowo)</span>
          <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </label>
      </div>
      <div className="create-panel-actions" style={{ marginBottom: 14 }}>
        <button className="btn-primary" onClick={saveDates} disabled={submitting || !from}>
          Zapisz daty
        </button>
        <button className="btn-ghost" onClick={onCancel} disabled={submitting}>
          Anuluj
        </button>
      </div>
      <div className="field-row">
        <label>Zakończ wcześniej, od dnia</label>
        <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        <button className="btn-ghost" onClick={endEarly} disabled={submitting || !endDate}>
          Zakończ
        </button>
      </div>
    </div>
  );
}

function DayOnlyExceptionForm({
  employeeId,
  siteId,
  onClose,
  onAdded,
  respondsToDecisionRequiredId,
}: {
  employeeId: string;
  siteId: string;
  onClose: () => void;
  onAdded: () => void;
  respondsToDecisionRequiredId: string | null;
}) {
  const [from, setFrom] = useState(isoToday());
  const [to, setTo] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await api.createDayOnlyException(employeeId, { site_id: siteId, effective_from: from, effective_to: to, responds_to_decision_required_id: respondsToDecisionRequiredId });
      onAdded();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="create-panel" style={{ marginTop: 14 }}>
      <p className="panel-hint" style={{ marginBottom: 10 }}>
        Ta osoba jest „tylko dniówka” — Nocka jest domyślnie zablokowana. Podaj, na jak długo ma być tymczasowo
        dozwolona.
      </p>
      {error && <div className="banner-error">{error}</div>}
      <div className="create-panel-fields" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <label>
          <span className="field-label">Od</span>
          <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label>
          <span className="field-label">Do</span>
          <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </label>
      </div>
      <div className="create-panel-actions">
        <button className="btn-primary" onClick={submit} disabled={submitting || !from || !to}>
          {submitting ? "Zapisywanie…" : "Zezwól tymczasowo"}
        </button>
        <button className="btn-ghost" onClick={onClose} disabled={submitting}>
          Anuluj
        </button>
      </div>
    </div>
  );
}

function AbsenceLog({
  records,
  employeeId,
  siteId,
  onChanged,
}: {
  records: AvailabilityRecordOut[];
  employeeId: string;
  siteId: string;
  onChanged: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);

  const endNow = async (r: AvailabilityRecordOut) => {
    try {
      await api.updateAvailability(employeeId, r.availability_id, {
        site_id: siteId, kind: r.kind, start_date: r.start_date, end_date: r.end_date, active: false,
      });
      onChanged();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    }
  };

  if (records.length === 0) return <p style={{ color: "var(--ink-faint)", fontSize: 13 }}>Brak zgłoszonych nieobecności.</p>;

  return (
    <>
      {error && <div className="banner-error">{error}</div>}
      {records.map((r) =>
        editingId === r.availability_id ? (
          <AbsenceEditRow
            key={r.availability_id}
            record={r}
            employeeId={employeeId}
            siteId={siteId}
            onDone={() => {
              setEditingId(null);
              onChanged();
            }}
            onCancel={() => setEditingId(null)}
          />
        ) : (
          <div key={r.availability_id} className={`absence-log-item${r.active ? "" : " absence-log-item-ended"}`}>
            <span>
              <strong>{AVAILABILITY_KIND_LABELS[r.kind] ?? r.kind}</strong> — od {r.start_date} do {r.end_date}
              {!r.active && " (zakończone)"}
            </span>
            <span style={{ display: "flex", gap: 8 }}>
              <button className="btn-ghost" onClick={() => setEditingId(r.availability_id)}>
                {r.active ? "Edytuj daty" : "Edytuj / przywróć"}
              </button>
              {r.active && (
                <button className="btn-ghost" onClick={() => endNow(r)}>
                  Zakończ teraz
                </button>
              )}
            </span>
          </div>
        ),
      )}
    </>
  );
}

function AbsenceEditRow({
  record,
  employeeId,
  siteId,
  onDone,
  onCancel,
}: {
  record: AvailabilityRecordOut;
  employeeId: string;
  siteId: string;
  onDone: () => void;
  onCancel: () => void;
}) {
  const [from, setFrom] = useState(record.start_date);
  const [to, setTo] = useState(record.end_date);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await api.updateAvailability(employeeId, record.availability_id, {
        site_id: siteId, kind: record.kind, start_date: from, end_date: to, active: true,
      });
      onDone();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="create-panel" style={{ marginBottom: 10 }}>
      <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>{AVAILABILITY_KIND_LABELS[record.kind] ?? record.kind}</p>
      {error && <div className="banner-error">{error}</div>}
      <div className="create-panel-fields" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <label>
          <span className="field-label">Od</span>
          <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label>
          <span className="field-label">Do</span>
          <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </label>
      </div>
      <div className="create-panel-actions">
        <button className="btn-primary" onClick={save} disabled={submitting || !from || !to}>
          Zapisz
        </button>
        <button className="btn-ghost" onClick={onCancel} disabled={submitting}>
          Anuluj
        </button>
      </div>
    </div>
  );
}

function AddAbsenceForm({
  employeeId,
  siteId,
  onClose,
  onAdded,
}: {
  employeeId: string;
  siteId: string;
  onClose: () => void;
  onAdded: () => void;
}) {
  const [kind, setKind] = useState<keyof typeof AVAILABILITY_KIND_LABELS>("UNAVAILABLE_24H");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await api.createAvailability(employeeId, {
        site_id: siteId, availability_id: crypto.randomUUID(), kind, start_date: from, end_date: to,
      });
      onAdded();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="create-panel" style={{ marginBottom: 18 }}>
      {error && <div className="banner-error">{error}</div>}
      <label style={{ display: "block", marginBottom: 14 }}>
        <span className="field-label">Powód</span>
        <select
          value={kind}
          onChange={(e) => setKind(e.target.value as keyof typeof AVAILABILITY_KIND_LABELS)}
          style={{ width: "100%", background: "var(--paper-light)", border: "1px solid var(--line)", borderRadius: 8, padding: "9px 12px", color: "var(--ink)" }}
        >
          {Object.entries(AVAILABILITY_KIND_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <div className="create-panel-fields" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <label>
          <span className="field-label">Od</span>
          <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label>
          <span className="field-label">Do</span>
          <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </label>
      </div>
      <div className="create-panel-actions">
        <button className="btn-primary" onClick={submit} disabled={submitting || !from || !to}>
          {submitting ? "Zapisywanie…" : "Zgłoś"}
        </button>
        <button className="btn-ghost" onClick={onClose} disabled={submitting}>
          Anuluj
        </button>
      </div>
    </div>
  );
}

function TargetHoursEditor({
  employeeId,
  siteId,
  month,
  value,
  onSaved,
}: {
  employeeId: string;
  siteId: string;
  month: string;
  value: number | null;
  onSaved: () => void;
}) {
  const [input, setInput] = useState(value !== null ? String(value) : "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setInput(value !== null ? String(value) : ""), [value]);

  const save = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await api.setTargetHours(employeeId, { site_id: siteId, month, target_hours: Number(input) });
      onSaved();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="field-row">
      <label>Godziny docelowe</label>
      {error && <div className="banner-error">{error}</div>}
      <input
        type="number"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={value === null ? "brak ustawionej wartości" : undefined}
        style={{ width: 120 }}
      />
      <button className="btn-primary" onClick={save} disabled={submitting || input === ""}>
        Zapisz
      </button>
      {value === null && <span style={{ color: "var(--ink-faint)", fontSize: 12 }}>brak ustawionej wartości</span>}
    </div>
  );
}
