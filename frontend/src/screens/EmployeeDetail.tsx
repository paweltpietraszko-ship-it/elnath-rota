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

const currentMonth = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
};

function cellActiveToday(cells: MatrixCellOut[], predicate: (c: MatrixCellOut) => boolean): boolean {
  const today = isoToday();
  return cells.some((c) => predicate(c) && c.applies_from && c.applies_to && c.applies_from <= today && c.applies_to >= today);
}

export default function EmployeeDetail({
  siteId,
  employeeId,
  onBack,
}: {
  siteId: string;
  siteName: string;
  employeeId: string;
  onBack: () => void;
}) {
  const [detail, setDetail] = useState<EmployeeDetailOut | null>(null);
  const [cells, setCells] = useState<MatrixCellOut[]>([]);
  const [month, setMonth] = useState(currentMonth());
  const [targetHours, setTargetHoursState] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddRestriction, setShowAddRestriction] = useState(false);
  const [showAddAbsence, setShowAddAbsence] = useState(false);

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
  const nockaBlocked = detail.employee.day_only ? !dayOnlyExceptionActive : cellActiveToday(cells, (c) => c.cell === "nocka");
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
          ✓ = solver może użyć tej osoby w tym wymiarze, ✕ = nie może. Szczegóły i edycja okresów — sekcje poniżej.
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
                  <StatusCell blocked={dniowkaBlocked} />
                </td>
                <td>
                  <StatusCell blocked={nockaBlocked} />
                </td>
                <td>
                  <button className={`matrix-box ${detail.membership.can_work_24h ? "matrix-box-on" : "matrix-box-off"}`} onClick={toggle24h}>
                    {detail.membership.can_work_24h ? "✓" : "✕"}
                  </button>
                </td>
                {[1, 2, 3, 4, 5, 6, 7].map((w) => (
                  <td key={w}>
                    <StatusCell blocked={cellActiveToday(cells, (c) => c.cell === "weekday" && c.weekday === w)} />
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title-row">
          <div>
            <h3>Ograniczenia: Dniówka / Nocka / dni tygodnia</h3>
            <p className="panel-hint">Każdy wiersz to osobny, niezależny okres — mogą się nakładać.</p>
          </div>
          <button className="btn-primary" onClick={() => setShowAddRestriction(true)}>
            + Nowe ograniczenie
          </button>
        </div>
        {showAddRestriction && (
          <AddRestrictionForm
            employeeId={employeeId}
            siteId={siteId}
            dayOnly={detail.employee.day_only}
            onClose={() => setShowAddRestriction(false)}
            onAdded={() => {
              setShowAddRestriction(false);
              load();
            }}
          />
        )}
        <RestrictionList cells={cells} employeeId={employeeId} siteId={siteId} onChanged={load} />
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
        <div className="field-row">
          <label>Miesiąc</label>
          <input type="month" value={month.slice(0, 7)} onChange={(e) => setMonth(`${e.target.value}-01`)} />
        </div>
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

function RestrictionList({
  cells,
  employeeId,
  siteId,
  onChanged,
}: {
  cells: MatrixCellOut[];
  employeeId: string;
  siteId: string;
  onChanged: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  if (cells.length === 0) return <p style={{ color: "var(--ink-faint)", fontSize: 13 }}>Brak aktywnych ograniczeń.</p>;

  const label = (c: MatrixCellOut) => {
    if (c.cell === "dniowka") return "Dniówka";
    if (c.cell === "nocka") return "Nocka";
    if (c.cell === "day_only_exception") return "Wyjątek: czasowa Nocka";
    if (c.cell === "weekday") return WEEKDAY_NAMES[(c.weekday ?? 1) - 1] ?? "Dzień tygodnia";
    return "Inne";
  };

  const endEarly = async (ruleId: string) => {
    try {
      await api.endMatrixRuleEarly(employeeId, ruleId, { site_id: siteId, effective_from: isoToday() });
      onChanged();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    }
  };

  return (
    <>
      {error && <div className="banner-error">{error}</div>}
      {cells.map((c) => (
        <div key={c.rule_id} className="absence-log-item">
          <span>
            <strong>{label(c)}</strong> — od {c.effective_from} do {c.effective_to ?? "bez końca"}
          </span>
          <button className="btn-ghost" onClick={() => endEarly(c.rule_id)}>
            Zakończ teraz
          </button>
        </div>
      ))}
    </>
  );
}

function AddRestrictionForm({
  employeeId,
  siteId,
  dayOnly,
  onClose,
  onAdded,
}: {
  employeeId: string;
  siteId: string;
  dayOnly: boolean;
  onClose: () => void;
  onAdded: () => void;
}) {
  const [kind, setKind] = useState<"dniowka" | "nocka" | "weekday" | "day_only_exception">("dniowka");
  const [weekday, setWeekday] = useState(1);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      if (kind === "dniowka") {
        await api.createShiftUnavailability(employeeId, { site_id: siteId, shift_kind: "D", effective_from: from, effective_to: to });
      } else if (kind === "nocka") {
        await api.createShiftUnavailability(employeeId, { site_id: siteId, shift_kind: "N", effective_from: from, effective_to: to });
      } else if (kind === "weekday") {
        await api.createWeekdayUnavailability(employeeId, { site_id: siteId, iso_weekday: weekday, effective_from: from, effective_to: to });
      } else {
        await api.createDayOnlyException(employeeId, { site_id: siteId, effective_from: from, effective_to: to });
      }
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
      <div className="chip-row" style={{ marginBottom: 14, flexWrap: "wrap" }}>
        <button className={`chip${kind === "dniowka" ? " chip-active" : ""}`} onClick={() => setKind("dniowka")}>
          Dniówka
        </button>
        <button className={`chip${kind === "nocka" ? " chip-active" : ""}`} onClick={() => setKind("nocka")}>
          Nocka
        </button>
        <button className={`chip${kind === "weekday" ? " chip-active" : ""}`} onClick={() => setKind("weekday")}>
          Dzień tygodnia
        </button>
        {dayOnly && (
          <button className={`chip${kind === "day_only_exception" ? " chip-active" : ""}`} onClick={() => setKind("day_only_exception")}>
            Wyjątek: czasowa Nocka
          </button>
        )}
      </div>
      {kind === "weekday" && (
        <label style={{ display: "block", marginBottom: 14 }}>
          <span className="field-label">Dzień tygodnia</span>
          <select
            value={weekday}
            onChange={(e) => setWeekday(Number(e.target.value))}
            style={{ background: "var(--paper-light)", border: "1px solid var(--line)", borderRadius: 8, padding: "9px 12px", color: "var(--ink)" }}
          >
            {WEEKDAY_NAMES.map((w, i) => (
              <option key={w} value={i + 1}>
                {w}
              </option>
            ))}
          </select>
        </label>
      )}
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
          {submitting ? "Zapisywanie…" : "Dodaj"}
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
  if (records.length === 0) return <p style={{ color: "var(--ink-faint)", fontSize: 13 }}>Brak zgłoszonych nieobecności.</p>;

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

  return (
    <>
      {error && <div className="banner-error">{error}</div>}
      {records.map((r) => (
        <div key={r.availability_id} className={`absence-log-item${r.active ? "" : " absence-log-item-ended"}`}>
          <span>
            <strong>{AVAILABILITY_KIND_LABELS[r.kind] ?? r.kind}</strong> — od {r.start_date} do {r.end_date}
            {!r.active && " (zakończone)"}
          </span>
          {r.active && (
            <button className="btn-ghost" onClick={() => endNow(r)}>
              Zakończ teraz
            </button>
          )}
        </div>
      ))}
    </>
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
