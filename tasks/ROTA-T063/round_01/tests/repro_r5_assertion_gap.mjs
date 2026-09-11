// Independent reproducer for the business-assertion gap in exact SHA 01acdd3.
// This mirrors assertFullCoverageAndClosedRoster from
// frontend/e2e/t063-business-outcomes.spec.ts.
function currentPredicate(assignments, allowedNames, daysInMonth) {
  const names = new Set(assignments.map((assignment) => assignment.employee_display_name));
  for (const name of names) {
    if (!allowedNames.includes(name)) return false;
  }
  return assignments.length === daysInMonth * 2;
}

const invalidSickLeaveCandidate = Array.from({ length: 60 }, () => ({
  employee_display_name: "D",
  start_datetime: "2026-09-12T05:00:00",
  end_datetime: "2026-09-12T17:00:00",
}));

if (!currentPredicate(invalidSickLeaveCandidate, ["A", "B", "C", "D", "E"], 30)) {
  throw new Error("reproducer setup error: current predicate unexpectedly rejected the candidate");
}

const invalidExternalCandidate = Array.from({ length: 60 }, (_, index) => ({
  employee_display_name: index === 0 ? "X1" : "A",
  start_datetime: index === 0 ? "2026-09-25T05:00:00" : "2026-09-01T05:00:00",
  end_datetime: index === 0 ? "2026-09-25T17:00:00" : "2026-09-01T17:00:00",
}));

if (!currentPredicate(invalidExternalCandidate, ["A", "B", "C", "D", "E", "X1"], 30)) {
  throw new Error("reproducer setup error: current predicate unexpectedly rejected external candidate");
}

console.log("REPRO PASS: current T063 predicate accepts D during SICK_LEAVE and X1 outside OKNO_7D.");
