# ROTA-T042 — ARCHITECT REVIEW R1

**Reviewed contract SHA:** `ac6294fae12f19b1c6b8e3c99362e1e4e244fb01`

**Base:** `main@071feb7cfaead0dbe8f514184fcb5ea614fa1cbf`

**Verdict:** **PASS — NO ADDITIONAL OWNER DECISION REQUIRED. READY FOR INDEPENDENT PREIMPLEMENTATION AUDIT. CC READ-ONLY UNTIL AUDIT PASS.**

## 1. Boundary / evidence

The reviewed branch is one documentation commit above the stated base and the contract commit changes only `tasks/ROTA-T042/brief.md`; no product code is part of the reviewed contract.

AUDIT-4 finding 8 independently establishes that the first of each adjacent pair of `assemble_planning_state()` calls in first PLAN and REPLAN is a discarded read: same connection, same arguments, no operation between the two calls, and all writes happen later. Finding 9 establishes that the schedule and decisions routers independently serialize the same four-field `DecisionRequiredPayload` content. Finding 10 establishes the UTC/local-day defect in Analytics, Export and MonthlyPlanning. Codex's independent AUDIT-4 review reconfirmed findings 8–10 on the T042 base.

`Overview.tsx` is correctly added to checkpoint A even though AUDIT-4 did not list it: its reachable `todayYearMonth()` uses the same `new Date().toISOString()` UTC conversion for a value whose product meaning is the coordinator's current local month. This is the same defect class, not a new product behavior.

## 2. Checkpoint A — local date

**PASS — contract is sufficiently frozen. No OWNER question remains.**

The brief explicitly defines the product meaning of "today": the calendar date on the coordinator's computer. Therefore no Site timezone, server timezone, persisted timezone, new preference or library is needed.

The proposed owner boundary is minimal:

- one frontend helper formats a supplied/current `Date` from `getFullYear()`, `getMonth()` and `getDate()`;
- only the four confirmed incorrect consumers move to it: Analytics, Export, MonthlyPlanning, Overview;
- existing correct local calculations in EmployeeDetail and Workspace remain untouched;
- diagnostics/real UTC timestamps remain UTC;
- form fields remain editable.

`Overview.tsx` currently derives its current month from `toISOString().slice(0, 7)`, so including it is mechanically justified.

### Audit note, not an OWNER decision

T42-A01/A02/A03 must exercise an actual Europe/Warsaw browser/runtime timezone (for example Playwright context timezone) at the fixed instant `2026-08-31T22:30:00Z`. A test executed in UTC while merely constructing that instant would not prove the local-date fix. This is test mechanics only; it does not require a contract change.

## 3. Checkpoint B — one PlanningState assembly

**PASS — technical-only change; no OWNER question remains.**

On the base:

- first PLAN with no current version calls `assemble_planning_state()` twice consecutively before `_create_first_version()`;
- REPLAN calls it twice consecutively before child creation;
- the first result in each pair is discarded;
- no state-changing operation occurs between the calls.

Removing only the discarded call preserves the existing safety rule that every PlanningState read which may fail happens before the irreversible ScheduleVersion write. The remaining call is still before the first write and is the state actually used by planning/child construction.

The brief correctly authorizes changing the old T009 audit test which intentionally fails the second call. Keeping a dead first call solely to satisfy that historical implementation-shape test would preserve the defect rather than the contract.

No cache, transaction redesign, assembler change or lifecycle change is justified by T042.

## 4. Checkpoint C — shared DecisionRequired payload adapter

**PASS — technical ownership consolidation; no OWNER question remains.**

The base has two reachable API paths serializing the same domain `DecisionRequiredPayload` fields independently:

- `blocking_shift_demands`;
- `blockers`;
- `load_blocker`;
- `unblocking_options`.

The top-level responses are intentionally different: schedule uses `DecisionRequiredPayloadOut`, while the Decisions endpoint uses the same content plus readback metadata (`decision_required_id`, site/month/version/requester/timestamp/linked actions). The brief explicitly preserves that distinction and consolidates only the common content in the `api` layer.

Therefore the implementer may choose the smallest internal Python shape (shared Pydantic element models + shared mapper/field adapter), but has no product freedom: endpoint URLs, field names, field types, nesting, optionality and frontend client contract must remain unchanged.

The acceptance test comparing real endpoint JSON is the correct oracle. A source-text equality test would not prove the public contract.

## 5. Scope assessment

The three checkpoints are independent and small enough for one task with three logical commits. They do not require a new entity, migration, endpoint, DTO field, solver rule or persistence rule.

Keeping the Coordinator Simulator in a later task is correct. Mixing its behavioral repairs into T042 would expand a small post-AUDIT-4 cleanup into a different product/test-tool contract.

No additional OWNER decision is required before the independent preimplementation audit.

## 6. Preimplementation audit focus

The independent auditor should verify exact contract SHA `ac6294fae12f19b1c6b8e3c99362e1e4e244fb01` and specifically confirm:

1. the local-date helper is local-calendar based and only the four incorrect consumers are migrated;
2. the midnight-boundary test genuinely runs in Europe/Warsaw (or an equivalent non-UTC local timezone proof), not accidentally in UTC;
3. PLAN/REPLAN each retain exactly one required pre-write assembly and no write moves before it;
4. the historical T009 test is adapted to fail that sole read and still proves no version/current-pointer side effect;
5. the shared API module owns only common `DecisionRequiredPayload` content and does not merge the two top-level endpoint contracts;
6. JSON shapes from PLAN/month readback/decision-detail remain byte-for-field compatible with the base contract;
7. `frontend/src/api/client.ts`, planning, persistence, schema and Simulator remain untouched unless the auditor finds a concrete blocker.

Expected audit verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, or
- `FAIL` with numbered concrete contract/implementation-seam defects.
