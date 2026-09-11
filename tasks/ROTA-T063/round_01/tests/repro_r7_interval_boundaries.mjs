// Independent positive reproducer for the full-interval predicates delivered
// on exact SHA 305d069.
function parseLocalIso(dateTime) {
  const [datePart, timePart] = dateTime.split("T");
  const [y, m, d] = datePart.split("-").map(Number);
  const [hh, mm, ss] = (timePart ?? "00:00:00").split(":").map(Number);
  return new Date(y, m - 1, d, hh, mm, ss || 0);
}

function fullDayRangeBounds(from, to) {
  const [fy, fm, fd] = from.split("-").map(Number);
  const [ty, tm, td] = to.split("-").map(Number);
  return {
    start: new Date(fy, fm - 1, fd, 0, 0, 0),
    end: new Date(ty, tm - 1, td + 1, 0, 0, 0),
  };
}

function collidesWithAbsence(assignment, from, to) {
  const { start, end } = fullDayRangeBounds(from, to);
  const assignmentStart = parseLocalIso(assignment.start_datetime);
  const assignmentEnd = parseLocalIso(assignment.end_datetime);
  return assignmentStart < end && assignmentEnd > start;
}

function isOutsideExternalWindow(assignment, from, to) {
  const { start, end } = fullDayRangeBounds(from, to);
  const assignmentStart = parseLocalIso(assignment.start_datetime);
  const assignmentEnd = parseLocalIso(assignment.end_datetime);
  return assignmentStart < start || assignmentEnd > end;
}

const nightEnteringSickLeave = {
  start_datetime: "2026-09-11T17:00:00",
  end_datetime: "2026-09-12T05:00:00",
};
const externalNightLeavingWindow = {
  start_datetime: "2026-09-18T17:00:00",
  end_datetime: "2026-09-19T05:00:00",
};

if (!collidesWithAbsence(nightEnteringSickLeave, "2026-09-12", "2026-09-18")) {
  throw new Error("absence boundary night was not rejected");
}
if (!isOutsideExternalWindow(externalNightLeavingWindow, "2026-09-12", "2026-09-18")) {
  throw new Error("external boundary night was not rejected");
}

console.log("REPRO PASS: both invalid overnight boundary intervals are rejected.");
