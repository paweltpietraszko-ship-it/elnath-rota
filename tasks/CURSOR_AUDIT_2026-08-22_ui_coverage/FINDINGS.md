# Cursor audit — T021 UI coverage vs `rota/application`

DATE: 2026-08-22
SHA: `e05dfb7` (`origin/main`)
REQUEST: received (uploaded to this agent; copied to `REQUEST.md` in this folder)
SPEC: **missing** — `arch/T021_spec.md` is not in the repo, not on any remote branch, and was not uploaded

No A / B / C findings against T021. Inventing a spec or scoring `arch/spec.md` instead would be a different document.

## Known-seven (acknowledged, not re-reported)

From REQUEST. Used only as a sanity check that the request was read. Not confirmed against T021_spec.md, because that file is not here. Line numbers are the live functions on `e05dfb7`.

1. `bootstrap.coordinator_context_completeness` — `rota/application/bootstrap.py:261`
   `bootstrap.month_plan_readiness` — `rota/application/bootstrap.py:316`
   REQUEST: already written up in T021 "COMPLETENESS AUDIT".
2. `durable_inputs.set_calendar_day` — `rota/application/durable_inputs.py:293`
   REQUEST: already flagged omitted.
3. `durable_inputs.update_site_profile` SiteProfile toggles — `rota/application/durable_inputs.py:356`
   REQUEST: already flagged omitted/not editable (`day_only_blocks_n`, `external_support_enabled`, `training_s_*`).
4. Coordinator account management
   `bootstrap.active_coordinators` — `rota/application/bootstrap.py:362`
   `bootstrap.all_coordinators` — `rota/application/bootstrap.py:367`
   `durable_inputs.update_coordinator` — `rota/application/durable_inputs.py:436`
   `durable_inputs.update_association` — `rota/application/durable_inputs.py:452`
   REQUEST: already flagged entirely unrepresented.
   (Also on this cluster, not named in the seven: `active_sites_for_coordinator` `:373`, `all_sites_for_coordinator` `:383`.)
5. `availability_matrix.employee_availability_matrix` — `rota/application/availability_matrix.py:53`
   REQUEST: already flagged as the purpose-built read-model for the per-employee matrix.
6. `precheck.precheck` — `rota/application/precheck.py:37`
   REQUEST: already flagged unplaced, low priority.
7. `open_month.open_month` — `rota/application/open_month.py:45`
   `open_month.months_with_schedule` — `rota/application/open_month.py:62`
   REQUEST: already flagged as a richer read-model several screens could ground against.

Cannot say "scan reproduced exactly these seven and nothing else" — that sentence requires reading T021_spec.md.

## A. OMISSIONS

Blocked. Need `arch/T021_spec.md`.

## B. INACCURACIES

Blocked. Need `arch/T021_spec.md` (file:line of the spec claim).

## C. DEPENDENCY/SEQUENCING CHECK

Blocked. Need the screen-to-screen links as written in T021_spec.md.
REQUEST examples (Decyzje koordynatora → Ręczna korekta / Panel / Obiekt reguły; Ostatnia akcja on Przegląd → Planowanie miesiąca; target_hours employee screen → Analityka) are not verified against spec text.

`REPORT.md` in this folder is a pre-spec inventory of the 56 public functions and code-side linkage facts. It is not A/B/C.

## Next input

Upload `arch/T021_spec.md` the same way as REQUEST (the file that has a "COMPLETENESS AUDIT" section at the top). Then A/B/C can be filled without re-reporting the seven above.
