# T021 round-1 mockup audit — response (2026-08-22)

Purpose: `tasks/ROTA-T021/round_01/tests/tests_r1.txt` (VERDICT: FAIL,
MAIN_SHA e05dfb7) listed six FINAL BLOCKERS before an implementation
contract. All later work on `arch/T021_spec.md` (dated 2026-08-22,
after that audit — Cursor second-pass + CC completeness audit) already
resolved most of them factually. This document is CC's own pass: cite
where each blocker is now answered, and state plainly which ones are
still open and need an owner/architect decision, not a re-derivation.
No new source code was read beyond what's cited — every claim below
traces to a `rota/` file path.

## A2 — backend surface coverage (nav-only screens)

FAIL said 5 nav-only screens were "not auditable." All five now have
per-screen fact sections in `T021_spec.md`, each citing its
`rota/application/*.py` entry points:
- Decyzje koordynatora → `T021_spec.md:560-604`
  (`memory_read.current_decision_required`, `decision_guidance.*`)
- Ręczna korekta → `T021_spec.md:606-641`
  (`rota/application/manual_edit.py`, 3 entry points + dry-run gap, see below)
- Historia i audyt → `T021_spec.md:643-691`
  (`rota/application/memory_read.py`, two independent streams)
- Analityka i bilanse → `T021_spec.md:693-723`
  (`rota/application/analytics_read.py`)
- Wydruk Grafiku → `T021_spec.md:725-759`
  (`rota/application/schedule_export.py`)

Backup/diagnostyka (`backup.backup_database`/`build_diagnostic_zip`,
`rota/application/backup.py:17-24`) — placement was `WYMAGA_DECYZJI` in
round 1. **RESOLVED**: both operate on the whole SQLite connection, not
one site (`backup_to` uses `conn.backup(dest_conn)`;
`diagnostics_payload` counts rows across every table). Confirmed home:
Workspace/Przedpokój screen, not any per-site screen —
`T021_spec.md:383-391`.

Training surface — round 1 flagged `save_site_membership`/
`mark_training_realized` as absent. **Fact, not a screen gap**:
`training.mark_training_realized` (`rota/application/training.py:122`)
is a side-effect hook fired when a TRAINEE `Assignment` is marked
REALIZED through the existing `apply_manual_correction` flow (Ręczna
korekta) — it is not a standalone feature needing its own nav item.
Readiness ("S/szkolenie") shows as a read-only badge on the
per-employee screen, derived from that history —
`T021_spec.md:92-98`. `save_site_membership` is the generic
add/edit-membership write, already covered by the "+ Dodaj osobę" /
Obsada flow.

**Still genuinely open** (owner/architect placement decision, not a
fact gap — from `T021_spec.md:30-58`, the completeness audit):
- `durable_inputs.set_calendar_day` (holiday/calendar config) — no
  screen anywhere.
- `durable_inputs.update_site_profile` toggles never shown/editable:
  `day_only_blocks_n`, `external_support_enabled`,
  `training_s_enabled`, `training_s_weekdays_only`,
  `training_s_default_readiness_threshold`. (Their sibling
  `rolling_7d_decision_threshold_hours` IS already shown, read-only, on
  Panel sterowania → Obiekt — plausible home for the rest, but not
  decided.)
- `durable_inputs.update_site` (display_name/active editing) — no
  screen.
- `bootstrap_or_resume_coordinator_context` ("+ Nowy obiekt" flow) — no
  screen; surfaced by the Cursor second-pass audit, needs placement.
- Coordinator account management
  (`bootstrap.active_coordinators`/`all_coordinators`,
  `durable_inputs.update_coordinator`/`update_association`) — explicitly
  ruled OUTSIDE current T021 scope, not merely unplaced.

## B1 — plan candidate count/shape

FAIL said the mockup hardcodes 2 candidates with invented names
("Równomierne obciążenie" etc.) and per-candidate deviation counts.
Confirmed against source, unchanged since round 1:
- `rota/planning/engine_types.py:46-51` —
  `PlanningResult.candidates: list[list[Assignment]]`. No name,
  strategy label, or per-candidate deviation-count field exists
  anywhere in the dataclass.
- `rota/planning/solver.py:462` (`_search_additional_candidates`) /
  `rota/planning/engine.py:164` (`_feasible_result`) — first candidate
  plus up to 2 alternatives, so the UI must handle exactly 1, 2, or 3
  candidates, never a fixed 2.

This is a fact, already usable to fix the mockup directly: render N
candidates (N∈{1,2,3}) generically, drop the invented strategy
names/labels, and derive any shown "odchylenia" count by counting
Deviations after validating each candidate — not from a backend field,
because none exists.

## B4 — SitePrintSettings shape

FAIL said the mockup showed a partial subset (missing
`site_print_name`, the D1-D5/N1-N5 work-code intervals, and U5/C5
reserve slots). **RESOLVED** — the full frozen shape is now written out
at `T021_spec.md:735-747`, confirmed against
`rota/persistence/site_repository.py:56-62`:
- `company_print_name`, `site_print_name` (both free text)
- `base_regime`: `"12h"` | `"24h"`
- `work_code_intervals`: exactly 10 keys `D1..D5,N1..N5`
  (`WORK_CODE_KEYS`), each an optional start/end interval with a FROZEN
  fixed duration per code (D1=12h, D2=4h, D3=24h, D4=2h, D5=24h,
  N1=12h, N2=16h, N3=24h, N4=24h, N5=24h — `FROZEN_WORK_CODE_HOURS`,
  never editable, this is a T020 print legend, not a legality table)
- `reserve_hours`: exactly 6 keys `U3,U4,U5,C3,C4,C5`
  (`RESERVE_SLOT_KEYS`), each an optional plain integer hour value

## Remaining non-fact items (implementation prerequisites, not blockers to this audit)

Two small missing application-layer wrappers (thin, low-risk, don't
block UI work — can call persistence directly short-term):
- `current_decision_required_months_for_site`
  (`rota/persistence/site_memory.py`) has no `memory_read.py` wrapper.
- `save_site_print_settings`
  (`rota/persistence/site_repository.py`) has no `durable_inputs.py`
  wrapper.

One new backend function genuinely not built yet, called foundational
by Paweł: a dry-run/preview for `apply_manual_correction`
(`T021_spec.md:625-641`) — shares steps 1-8 with the real call, stops
before `lifecycle.create_schedule_version`, returns would-be Deviations
instead of persisting. Needed for the "zmiana→pytanie→zapisz/odrzuć"
flow on Ręczna korekta.

## Net effect on round-1's FINAL BLOCKERS list

| Round-1 blocker | Status |
|---|---|
| decide backup surface/placement | RESOLVED — workspace screen, confirmed |
| decide training surface inclusion | RESOLVED — not a screen, derived badge + existing korekta flow; toggle *editing* still open (see A2) |
| candidate selector factual for 1..3 | RESOLVED as fact; mockup fix is a straightforward implementation task |
| remove invented candidate names/counts | RESOLVED as fact, same as above |
| complete SitePrintSettings shape | RESOLVED — full shape documented and cited |
| auditable nav-only screen content | RESOLVED — all 5 screens have fact sections |

Nothing above required a design decision from CC — every resolution is
a citation to existing frozen code or to Paweł's own prior ruling
already recorded in `T021_spec.md`. The genuinely open items (calendar
config, SiteProfile toggle editing, Site edit, "+ Nowy obiekt" flow)
are placement/priority calls for the owner/architect, not facts CC can
resolve unilaterally.
