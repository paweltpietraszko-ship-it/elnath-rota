// ROTA-T042 Checkpoint A (tasks/ROTA-T042/brief.md §2): "dzisiaj" is the
// coordinator's local calendar date. toISOString() converts to UTC first,
// so it reports yesterday's date between local midnight and the UTC offset
// (e.g. 00:30 Europe/Warsaw on 2026-09-01 is still 2026-08-31T22:30:00Z).
export function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function todayYearMonth(): string {
  return todayIso().slice(0, 7);
}
