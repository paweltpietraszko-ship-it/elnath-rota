# ROTA-T023 — OWNER DECISION: NIGHT SHIFT DATE ANCHOR

DATE: 2026-08-22
STATUS: ACCEPTED OWNER DECISION
SCOPE: T023 absence-hours accounting and U/C presentation

## Rule

A shift from 17:00 to 05:00 belongs in full to the calendar date on which the shift starts.

- Do not split the shift at midnight.
- Do not calculate separate pre-midnight and post-midnight absence hours.
- `SICK_LEAVE` or `LEAVE_GRANTED` covers this shift for T023 accounting only when its inclusive date range contains the shift start date.
- Presentation uses one whole-shift U/C result; it must not create partial symbols for the two calendar dates.

## Binding examples

1. Shift: 2027-03-01 17:00 → 2027-03-02 05:00. Absence starts 2027-03-02. Result: the shift is not converted to U/C and contributes no T023 absence hours for 2027-03-02.
2. Shift: 2027-03-01 17:00 → 2027-03-02 05:00. Absence includes 2027-03-01. Result: the whole shift is covered and contributes its full scheduled duration to T023 absence hours on 2027-03-01.

This decision is incorporated into `arch/T023_absence_hours_architect_brief.md`, Section 6.
