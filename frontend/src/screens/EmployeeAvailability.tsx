import { useState } from "react";
import { DateRange, DayPicker } from "@daypicker/react";
import "@daypicker/react/style.css";
import { api, AvailabilityRecordOut } from "../api/client";

// ROTA-DELEGACJA-ABSENCE-KIND brief.md section 11: mechanical extraction of
// the Availability block out of EmployeeDetail.tsx (AbsenceLog/
// AbsenceEditRow/AddAbsenceForm, unchanged behavior) plus the new DELEGACJA
// handling. EmployeeDetail.tsx only imports and embeds <EmployeeAvailability>.

const AVAILABILITY_KIND_LABELS: Record<string, string> = {
  DAY_SHIFT_OFF: "Wolne w dzień",
  UNAVAILABLE_24H: "Ogólna niedostępność",
  LEAVE_PLAN: "Urlop (planowany)",
  LEAVE_GRANTED: "Urlop (przyznany)",
  SICK_LEAVE: "Zwolnienie chorobowe",
  // ROTA-T065-ORDINARY-TIME-AVAILABILITY: ORDINARY-only, ordinary shop
  // employees' real hourly availability -- never shown/selectable for
  // OCHRONA (section 6/9).
  UNAVAILABLE_TIME_WINDOW: "Niedostępność godzinowa",
  // ROTA-DELEGACJA-ABSENCE-KIND: both regimes.
  DELEGACJA: "Delegacja",
};

function monthBoundsIso(workingMonth: string): { firstDay: string; lastDay: string } {
  const [year, month] = workingMonth.split("-").map(Number);
  const lastDate = new Date(year, month, 0).getDate();
  return { firstDay: `${workingMonth}-01`, lastDay: `${workingMonth}-${String(lastDate).padStart(2, "0")}` };
}

function monthLabel(workingMonth: string): string {
  const [year, month] = workingMonth.split("-").map(Number);
  return new Date(year, month - 1, 1).toLocaleString("pl-PL", { month: "long", year: "numeric" });
}

// ROTA-T064 (brief section 6): local calendar date, no UTC shift.
function toLocalIso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function AbsenceLog({
  records,
  employeeId,
  siteId,
  workingMonth,
  onChanged,
}: {
  records: AvailabilityRecordOut[];
  employeeId: string;
  siteId: string;
  workingMonth: string;
  onChanged: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);

  const endNow = async (r: AvailabilityRecordOut) => {
    try {
      await api.updateAvailability(employeeId, r.availability_id, {
        site_id: siteId, kind: r.kind, start_date: r.start_date, end_date: r.end_date, active: false,
        start_time: r.start_time, end_time: r.end_time,
        // ROTA-DELEGACJA-ABSENCE-KIND: the write boundary requires
        // delegation_hours on every append of an existing DELEGACJA
        // family, including this deactivation -- resend the current value.
        delegation_hours: r.delegation_hours,
      });
      onChanged();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    }
  };

  const { firstDay, lastDay } = monthBoundsIso(workingMonth);
  const label = monthLabel(workingMonth);
  const visible = records
    .filter((r) => r.start_date <= lastDay && r.end_date >= firstDay)
    .sort((a, b) => a.start_date.localeCompare(b.start_date) || a.end_date.localeCompare(b.end_date) || a.availability_id.localeCompare(b.availability_id));

  return (
    <>
      <p className="panel-hint" style={{ marginTop: 0 }}>Miesiąc roboczy: {label}</p>
      {error && <div className="banner-error">{error}</div>}
      {visible.length === 0 ? (
        <p style={{ color: "var(--ink-faint)", fontSize: 13 }}>Brak nieobecności w wybranym miesiącu.</p>
      ) : (
        visible.map((r) =>
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
                {r.start_time && r.end_time && `, ${r.start_time}–${r.end_time}`}
                {r.kind === "DELEGACJA" && r.delegation_hours != null && `, ${r.delegation_hours}h/dzień`}
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
        )
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
  const isWindow = record.kind === "UNAVAILABLE_TIME_WINDOW";
  const isDelegacja = record.kind === "DELEGACJA";
  const [fromTime, setFromTime] = useState(record.start_time ?? "");
  const [toTime, setToTime] = useState(record.end_time ?? "");
  const [delegationHours, setDelegationHours] = useState<string>(
    record.delegation_hours != null ? String(record.delegation_hours) : "",
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parsedDelegationHours = Number(delegationHours);
  const delegationHoursValid = !isDelegacja || (delegationHours !== "" && parsedDelegationHours > 0);

  const save = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await api.updateAvailability(employeeId, record.availability_id, {
        site_id: siteId, kind: record.kind, start_date: from, end_date: to, active: true,
        start_time: isWindow ? fromTime : null, end_time: isWindow ? toTime : null,
        delegation_hours: isDelegacja ? parsedDelegationHours : null,
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
        {isWindow && (
          <>
            <label>
              <span className="field-label">Od godziny</span>
              <input type="time" step={3600} value={fromTime} onChange={(e) => setFromTime(e.target.value)} />
            </label>
            <label>
              <span className="field-label">Do godziny</span>
              <input type="time" step={3600} value={toTime} onChange={(e) => setToTime(e.target.value)} />
            </label>
          </>
        )}
        {isDelegacja && (
          <label>
            <span className="field-label">Godziny delegacji (dziennie)</span>
            <input
              type="number"
              min={1}
              value={delegationHours}
              onChange={(e) => setDelegationHours(e.target.value)}
            />
          </label>
        )}
      </div>
      <div className="create-panel-actions">
        <button
          className="btn-primary"
          onClick={save}
          disabled={submitting || !from || !to || (isWindow && (!fromTime || !toTime || fromTime >= toTime)) || !delegationHoursValid}
        >
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
  workingMonth,
  regime,
  delegationDefaultHours,
  onClose,
  onAdded,
}: {
  employeeId: string;
  siteId: string;
  workingMonth: string;
  regime: "OCHRONA" | "ORDINARY";
  delegationDefaultHours: number | null;
  onClose: () => void;
  onAdded: () => void;
}) {
  const [kind, setKind] = useState<keyof typeof AVAILABILITY_KIND_LABELS>("UNAVAILABLE_24H");
  const [range, setRange] = useState<DateRange | undefined>(undefined);
  const isWindow = kind === "UNAVAILABLE_TIME_WINDOW";
  const isDelegacja = kind === "DELEGACJA";
  const [fromTime, setFromTime] = useState("");
  const [toTime, setToTime] = useState("");
  const [delegationHours, setDelegationHours] = useState<string>(
    delegationDefaultHours != null ? String(delegationDefaultHours) : "",
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [year, month] = workingMonth.split("-").map(Number);
  const defaultMonth = new Date(year, month - 1, 1);
  // ROTA-T065-ORDINARY-TIME-AVAILABILITY section 6/9: UNAVAILABLE_TIME_WINDOW
  // exists only for ORDINARY. DELEGACJA (ROTA-DELEGACJA-ABSENCE-KIND) is
  // available for both regimes -- no filter needed for it.
  const availableKinds = Object.entries(AVAILABILITY_KIND_LABELS).filter(
    ([value]) => regime === "ORDINARY" || value !== "UNAVAILABLE_TIME_WINDOW",
  );

  const parsedDelegationHours = Number(delegationHours);
  const delegationHoursValid = !isDelegacja || (delegationHours !== "" && parsedDelegationHours > 0);

  // ROTA live UX finding (2026-09-17, owner click-through): react-day-
  // picker's own default range logic completes a 1-day range on the
  // FIRST click (addToRange with no `min` set), which immediately enables
  // "Zgłoś" -- a coordinator meaning to mark a multi-day absence could
  // submit a wrong 1-day one without a deliberate second click, then have
  // to reopen edit to fix the end date. Owner's choice: always require an
  // explicit second click, even for a single-day absence (click the same
  // day twice). Ignores the library's own auto-completed `selected` value
  // (2nd onSelect arg is the raw clicked day) and tracks the two clicks
  // ourselves.
  const handleSelectDay = (triggerDate: Date) => {
    setRange((prev) => {
      if (!prev?.from || prev.to) {
        return { from: triggerDate, to: undefined };
      }
      return triggerDate < prev.from
        ? { from: triggerDate, to: prev.from }
        : { from: prev.from, to: triggerDate };
    });
  };

  const submit = async () => {
    if (!range?.from || !range?.to) return;
    if (isWindow && (!fromTime || !toTime || fromTime >= toTime)) return;
    if (isDelegacja && !delegationHoursValid) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.createAvailability(employeeId, {
        site_id: siteId, availability_id: crypto.randomUUID(), kind,
        start_date: toLocalIso(range.from), end_date: toLocalIso(range.to),
        start_time: isWindow ? fromTime : null, end_time: isWindow ? toTime : null,
        delegation_hours: isDelegacja ? parsedDelegationHours : null,
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
          {availableKinds.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {isWindow && (
        <div className="create-panel-fields" style={{ gridTemplateColumns: "1fr 1fr", marginBottom: 14 }}>
          <label>
            <span className="field-label">Niedostępny od godziny</span>
            <input type="time" step={3600} value={fromTime} onChange={(e) => setFromTime(e.target.value)} />
          </label>
          <label>
            <span className="field-label">do godziny</span>
            <input type="time" step={3600} value={toTime} onChange={(e) => setToTime(e.target.value)} />
          </label>
        </div>
      )}
      {isDelegacja && (
        <div style={{ marginBottom: 14 }}>
          {delegationDefaultHours == null ? (
            <div className="banner-error">
              Ten obiekt nie ma jeszcze ustawionej domyślnej liczby godzin delegacji — ustaw ją najpierw w panelu sterowania.
            </div>
          ) : (
            <label style={{ display: "block", maxWidth: 220 }}>
              <span className="field-label">Godziny delegacji (dziennie)</span>
              <input
                type="number"
                min={1}
                value={delegationHours}
                onChange={(e) => setDelegationHours(e.target.value)}
              />
            </label>
          )}
        </div>
      )}
      <DayPicker
        mode="range"
        selected={range}
        onSelect={(_range, triggerDate) => handleSelectDay(triggerDate)}
        defaultMonth={defaultMonth}
        data-diag-element="absence-range-picker"
      />
      <p className="field-hint">
        {range?.from && range?.to
          ? `Wybrany zakres: ${toLocalIso(range.from)} – ${toLocalIso(range.to)}`
          : range?.from
            ? "Kliknij datę końcową (tę samą, jeśli to jeden dzień)."
            : "Wybierz datę początkową."}
      </p>
      <div className="create-panel-actions">
        <button
          className="btn-primary"
          onClick={submit}
          disabled={
            submitting || !range?.from || !range?.to ||
            (isWindow && (!fromTime || !toTime || fromTime >= toTime)) ||
            (isDelegacja && (delegationDefaultHours == null || !delegationHoursValid))
          }
        >
          {submitting ? "Zapisywanie…" : "Zgłoś"}
        </button>
        <button className="btn-ghost" onClick={onClose} disabled={submitting}>
          Anuluj
        </button>
      </div>
    </div>
  );
}

export default function EmployeeAvailability({
  employeeId,
  siteId,
  workingMonth,
  regime,
  delegationDefaultHours,
  records,
  showAddAbsence,
  onShowAddAbsence,
  onChanged,
}: {
  employeeId: string;
  siteId: string;
  workingMonth: string;
  regime: "OCHRONA" | "ORDINARY";
  delegationDefaultHours: number | null;
  records: AvailabilityRecordOut[];
  showAddAbsence: boolean;
  onShowAddAbsence: (show: boolean) => void;
  onChanged: () => void;
}) {
  return (
    <div className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Nieobecności (w tym Ogólna dostępność)</h3>
          <p className="panel-hint">Urlop, chorobowe, ogólna niedostępność i delegacja — wszystko w jednym miejscu.</p>
        </div>
        <button className="btn-primary" onClick={() => onShowAddAbsence(true)}>
          + Zgłoś nieobecność
        </button>
      </div>
      {showAddAbsence && (
        <AddAbsenceForm
          employeeId={employeeId}
          siteId={siteId}
          workingMonth={workingMonth}
          regime={regime}
          delegationDefaultHours={delegationDefaultHours}
          onClose={() => onShowAddAbsence(false)}
          onAdded={() => {
            onShowAddAbsence(false);
            onChanged();
          }}
        />
      )}
      <AbsenceLog records={records} employeeId={employeeId} siteId={siteId} workingMonth={workingMonth} onChanged={onChanged} />
    </div>
  );
}
