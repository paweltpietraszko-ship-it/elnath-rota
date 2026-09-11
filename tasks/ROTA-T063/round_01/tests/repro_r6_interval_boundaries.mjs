// Independent reproducer for exact SHA 9c7cb55.
// Mirrors the new date-only predicates and contrasts them with the full
// interval semantics used by production eligibility.
function dateOnly(dateTime) {
  return dateTime.slice(0, 10);
}

function newAbsencePredicateAccepts(assignment, employeeName, from, to) {
  const collides =
    assignment.employee_display_name === employeeName &&
    dateOnly(assignment.start_datetime) >= from &&
    dateOnly(assignment.start_datetime) <= to;
  return !collides;
}

function newExternalPredicateAccepts(assignment, externalName, from, to) {
  const outOfWindow =
    assignment.employee_display_name === externalName &&
    (dateOnly(assignment.start_datetime) < from || dateOnly(assignment.start_datetime) > to);
  return !outOfWindow;
}

const nightEnteringSickLeave = {
  employee_display_name: "D",
  start_datetime: "2026-09-11T17:00:00",
  end_datetime: "2026-09-12T05:00:00",
};

if (!newAbsencePredicateAccepts(nightEnteringSickLeave, "D", "2026-09-12", "2026-09-18")) {
  throw new Error("setup error: new absence predicate unexpectedly rejected boundary night");
}

const externalNightLeavingWindow = {
  employee_display_name: "X1",
  start_datetime: "2026-09-18T17:00:00",
  end_datetime: "2026-09-19T05:00:00",
};

if (!newExternalPredicateAccepts(externalNightLeavingWindow, "X1", "2026-09-12", "2026-09-18")) {
  throw new Error("setup error: new external predicate unexpectedly rejected boundary night");
}

console.log("REPRO PASS: date-only assertions accept both invalid overnight boundary intervals.");
