# ROTA-T020 — CHECKPOINT B OWNER DECISIONS 05

STATUS: OWNER CORRECTION — AUTHORITATIVE ABSENCE PRESENTATION SEMANTICS
DATE: 2026-08-20
TASK_ID: ROTA-T020
SUPERSEDES: tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_03.md, tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_04.md
RETRACTS_BLOCKER: tasks/ROTA-T020/ARCHITECT_PLANNING_GAP_01.md

## 1. CORE CORRECTION — DO NOT CHANGE SOLVER ABSENCE COVERAGE

The operational solver is already responsible for real Site coverage and must keep that responsibility unchanged for T020.

When an Employee is on `LEAVE_GRANTED` or `SICK_LEAVE`:

- the Employee is not operationally assigned to perform the affected Site demand;
- the solver distributes the real shifts among Employees who are actually eligible to work;
- absence hours do not reduce the Site demand that must be covered;
- T020 MUST NOT require the solver to create a second, nominal Assignment for the absent Employee;
- T020 MUST NOT change Assignment coverage semantics, solver eligibility, ScheduleVersion, or demand accounting merely to print U/C.

Example: if a Site has 720h of real work to cover in the month, it still has 720h to cover even if one LOCAL Employee has 168h of leave/sickness presentation. The 168h U/C presentation does not subtract from the Site's 720h operational coverage.

## 2. T020 OWNS THE PAPER PRESENTATION OF ABSENCE HOURS

The frozen owner brief already defines `D1..D5`, `N1..N5`, `U1..U5`, and `C1..C5` as a presentation convention. The solver does not assign those codes.

For absence presentation, T020 reads the canonical absence/accounting result supplied by the existing T018/WorkBalance semantics and fills otherwise empty qualifying cells in the printed employee row.

T020 therefore creates presentation symbols, not operational Assignments.

Examples:

- full-month U/C whose canonical absence total for the month is 168h -> the printed row contains an exact 168h presentation decomposition;
- 40h U/C -> the printed row contains an exact 40h presentation decomposition;
- the real Site coverage remains whatever the operational solver assigned and is not reduced by those presentation symbols.

## 3. PLAN/WYK FOR ABSENCE IS A PRINT CONVENTION

For each presentation position chosen by the deterministic absence decomposition:

- PLAN prints the corresponding D/N presentation symbol;
- WYK below it prints the corresponding U/C presentation symbol of the same value;
- these paired cells document the monthly paper convention for the Employee;
- they do NOT assert that the absent Employee had an operational Assignment to a real ShiftDemand at that position.

Frozen owner example for 40h leave:

- PLAN: `D1 / D1 / N2` = `12 + 12 + 16 = 40h`;
- WYK: `U1 / U1 / U2` = `12 + 12 + 16 = 40h`.

For sickness the analogous WYK symbols are `C*`.

This is distinct from printing an actual work Assignment. Actual work cells must still map from the real configured Assignment interval/work-period to the correct D/N code. Absence-filled blank cells use the frozen absence decomposition algorithm, not a fabricated demand or historical Assignment.

## 4. DETERMINISTIC ABSENCE FILLING

T020 follows the owner-brief rules already frozen:

1. use only non-zero denominations allowed by the Site base regime;
2. require an exact sum;
3. minimize the number of symbols;
4. use a deterministic tie-break;
5. place the symbols deterministically in the first qualifying absence days/cells;
6. place the corresponding U/C symbols directly under the paired PLAN positions.

Existing real work assignments on non-absence cells remain sourced from scheduling truth and are not replaced by this presentation fill.

## 5. ONE-DAY / NON-DECOMPOSABLE ABSENCE

A one-day absence can produce an accounting total (for example 8h under the existing T018 qualified-workday rule) for which the currently configured print legend has no exact decomposition.

That is a T020 presentation decision problem, not permission to alter operational solver coverage.

If an exact decomposition does not exist:

- T020 must not round;
- T020 must not invent a D/N/U/C value;
- T020 must not alter Assignment or ScheduleVersion;
- T020 returns an explicit coordinator decision problem;
- the coordinator may configure an allowed reserve legend slot for the Site/regime, after which regeneration is deterministic.

## 6. ROW POPULATION REMAINS FROZEN

The prior owner row-population decision remains valid:

- enabled LOCAL Employee -> row is present even with zero operational Assignments in the month;
- EXTERNAL_SUPPORT Employee -> row is present only if that Employee actually has an effective Assignment on the printed Site/month;
- EXTERNAL_SUPPORT with zero effective Assignment -> no empty row.

This is why a LOCAL Employee who is absent for the whole month can have an operationally empty schedule from the solver while T020 still prints the required U/C presentation in that Employee's row.

## 7. EFFECT ON THE ROUND-4 CODEX FINDING

Codex Round 4 correctly proved that the current planning model does not persist a second nominal Assignment layer for absent Employees.

That finding was correct against the then-stated architect premise, but the premise is now withdrawn.

The owner does NOT require a second nominal Assignment layer for T020. Therefore the absence of such a layer is NOT a T020 planning blocker.

T020 must use presentation decomposition from canonical absence/accounting data while leaving operational coverage unchanged.

## 8. CHECKPOINT STATUS

- Checkpoint A: ACCEPTED / FROZEN.
- Operational solver absence behavior: OUT OF SCOPE FOR CHANGE IN T020; keep real coverage semantics.
- Previous `ARCHITECT_PLANNING_GAP_01` blocker: WITHDRAWN by owner correction.
- T020 Checkpoint B architecture: MAY PROCEED, subject to the remaining normal B contract/audit gates.
- Production CC: still requires a frozen full Checkpoint B implementation contract and independent preimplementation audit before coding.
