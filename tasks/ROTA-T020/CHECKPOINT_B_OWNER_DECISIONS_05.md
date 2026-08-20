# ROTA-T020 — CHECKPOINT B OWNER DECISIONS 05

STATUS: OWNER CORRECTION — AUTHORITATIVE ABSENCE PRESENTATION SEMANTICS
DATE: 2026-08-20
TASK_ID: ROTA-T020
SUPERSEDES:
- tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_01.md — old B-PD-01 interpretation that T020 must never consume the canonical 8h/workday absence result for presentation
- tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_03.md
- tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_04.md
SUPERSEDES_IN_PART:
- tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_02.md sections 2–4 where they conflict with this document
PRESERVES:
- tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_02.md section 1 row-population decision
RETRACTS_BLOCKER: tasks/ROTA-T020/ARCHITECT_PLANNING_GAP_01.md

## 1. CORE CORRECTION — DO NOT CHANGE SOLVER ABSENCE COVERAGE

The operational solver is already responsible for real Site coverage and must keep that responsibility unchanged for T020.

When an Employee is on `LEAVE_GRANTED` or `SICK_LEAVE`:

- the Employee is not operationally assigned to perform the affected Site demand;
- the solver distributes the real shifts among Employees who are actually eligible to work;
- absence hours do not reduce the Site demand that must be covered;
- T020 MUST NOT require the solver to create a second nominal Assignment for the absent Employee;
- T020 MUST NOT change Assignment coverage semantics, solver eligibility, ScheduleVersion or demand accounting merely to print U/C.

Example fixed by the owner: if a Site has 720h of real work to cover in the month, it still has 720h to cover even if one LOCAL Employee has 168h of leave/sickness presentation. The 168h U/C presentation does not subtract from the Site's 720h operational coverage.

## 2. T020 OWNS THE PAPER PRESENTATION OF ABSENCE HOURS

The frozen owner brief defines `D1..D5`, `N1..N5`, `U1..U5` and `C1..C5` as a presentation convention. The solver does not assign these codes.

For absence presentation, T020 reads the canonical absence-accounting result supplied by the existing T018 semantics and fills otherwise empty qualifying cells in the printed Employee row.

T020 therefore creates presentation symbols, not operational Assignments.

Examples:

- full-month U/C whose canonical absence total for the month is 168h -> the printed LOCAL row contains an exact 168h presentation decomposition;
- 40h U/C -> the printed LOCAL row contains an exact 40h presentation decomposition;
- real Site coverage remains whatever the operational solver assigned and is not reduced by those presentation symbols.

This supersedes the earlier interpretation in `CHECKPOINT_B_OWNER_DECISIONS_01.md` that T020 must never consume the global T018 8h/workday result for print presentation. T020 may consume that canonical accounting result for presentation, but must not pretend that it is an operational Assignment or duplicate it across Sites.

## 3. PLAN/WYK FOR ABSENCE IS A PRINT CONVENTION

For each presentation position chosen by deterministic absence decomposition:

- PLAN prints the corresponding D/N presentation symbol;
- WYK below it prints the corresponding U/C presentation symbol of the same value;
- these paired cells document the paper convention for the Employee;
- they do NOT assert that the absent Employee had an operational Assignment to a real ShiftDemand at that position.

Frozen owner example for 40h leave:

- PLAN: `D1 / D1 / N2` = `12 + 12 + 16 = 40h`;
- WYK: `U1 / U1 / U2` = `12 + 12 + 16 = 40h`.

For sickness the analogous WYK symbols are `C*`.

This is distinct from printing a real work Assignment. Actual work cells map from real Assignment/work-period truth. Absence-filled cells use the frozen print decomposition and do not fabricate demand or historical Assignment provenance.

## 4. DETERMINISTIC ABSENCE FILLING

T020 follows the owner-brief rules already frozen:

1. use only non-zero denominations allowed by the Site base regime;
2. require an exact sum;
3. minimize the number of symbols;
4. use one deterministic tie-break;
5. place symbols deterministically in the first qualifying absence workday cells;
6. place corresponding U/C symbols directly below the paired PLAN symbols.

Existing real work Assignments remain sourced from scheduling truth and are not replaced by presentation fill.

## 5. ONE-DAY / NON-DECOMPOSABLE ABSENCE

A one-day absence can produce an accounting total, for example 8h under current T018 qualified-workday accounting, for which the effective print legend has no exact legal representation.

That is a T020 presentation decision problem, not a solver problem.

If an exact decomposition does not exist:

- T020 does not round;
- T020 does not invent a D/N/U/C value;
- T020 does not alter Assignment or ScheduleVersion;
- T020 returns an explicit coordinator presentation problem;
- coordinator may configure an allowed reserve legend slot and regenerate.

A configured reserve U/C value is useful only when the effective presentation rules also contain a legal equal-value PLAN D/N pair. T020 must not create multiple symbols inside one day cell unless a future owner amendment explicitly permits that visual convention.

## 6. ROW POPULATION — PRESERVED OWNER DECISION

The owner row-population rule from `CHECKPOINT_B_OWNER_DECISIONS_02.md` section 1 remains binding:

- enabled LOCAL Employee -> row is present even with zero operational Assignments in the month;
- EXTERNAL_SUPPORT Employee -> row is present only if that Employee actually has an effective Assignment on the printed Site/month;
- EXTERNAL_SUPPORT with zero effective Assignment -> no empty row;
- a real effective Assignment is sufficient to include the Employee regardless of membership kind.

This is why a LOCAL Employee who is absent for the whole month can have an operationally empty solver schedule while T020 still prints U/C presentation in that Employee's row.

## 7. SITE-LOCAL FAIL-CLOSED BOUNDARY

Availability/T018 absence accounting belongs to the Employee and currently has no Site ownership field.

The owner has not authorized duplication of the same U/C presentation across multiple LOCAL Site printouts and the architect must not guess such ownership.

Therefore the first production T020 scope is fail-closed:

- U/C presentation is generated only for an enabled LOCAL Employee on the printed Site;
- if that Employee has exactly one enabled LOCAL Site membership, that Site may present the canonical T018 monthly absence result;
- if that Employee has more than one enabled LOCAL Site membership and qualifying U/C must be presented, T020 returns an explicit `ABSENCE_SITE_AMBIGUOUS` problem and produces no PDF;
- EXTERNAL_SUPPORT presence never causes global U/C accounting to be attributed to the external-support Site;
- Site ownership is not inferred from readiness, target hours, existing Assignment distribution or arbitrary membership ordering.

This is a safe first-scope boundary, not a new persistent absence-allocation model.

## 8. EFFECT ON ROUND 4

Codex Round 4 correctly proved that the current planning model does not persist a second nominal Assignment layer for absent Employees.

That finding was correct against the then-stated architect premise, but that premise is withdrawn.

The owner does NOT require a second nominal Assignment layer for T020. Therefore the absence of such a layer is NOT a T020 planning blocker.

Round 4 remains historical evidence about solver behavior only.

## 9. COMMUNICATION RULE FOR UNDEFINED PRODUCT CASES

The architect and implementers must not infer missing real scheduling semantics from current code.

If a case changes real scheduling behavior and current owner material does not define it unambiguously, ask the owner before freezing that behavior.

Technical fail-closed handling and implementation choices that do not change scheduling behavior remain architect-owned.

## 10. CHECKPOINT STATUS

- Checkpoint A: ACCEPTED / FROZEN.
- Operational solver absence behavior: OUT OF SCOPE FOR CHANGE IN T020.
- Previous planning blocker: WITHDRAWN.
- Row population: CLOSED.
- U/C presentation semantics: CLOSED by this authoritative correction.
- T020 Checkpoint B architecture: MAY PROCEED.
- Production CC still requires a frozen full Checkpoint B contract and independent preimplementation PASS.
