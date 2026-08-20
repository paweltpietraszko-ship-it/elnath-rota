# ROTA-T020 Checkpoint A — printable schedule PDF prototype

Scope: `tasks/ROTA-T020/brief.md` Checkpoint A only. This directory is a
pipeline/prototype artifact, not production code. Nothing here is
imported by `rota/**`, and the script never opens the Rota database.

## What this is

`render_samples.py` generates two static, printable A3-landscape demo
PDFs on fully fictional data:

- `schedule_12h.pdf` — a Site running the base **12h** regime
- `schedule_24h.pdf` — a Site running the base **24h** regime

Both show the paper-schedule convention (month in columns, employees in
rows, a `PLAN` and a `WYK` sub-row per employee, hour summaries, and the
owner's frozen legend table) so the owner can accept or reject the real
visual before any production PDF generator or Rota-data read model is
built (Checkpoint B).

## Run it

```
pip install -r requirements.txt
python render_samples.py
```

Regenerating overwrites `schedule_12h.pdf` and `schedule_24h.pdf` in
this same directory. All data (employee names, dates, provenance ids,
revision ids) is deterministic and synthetic — running it twice on the
same day produces the same content except for the `Wygenerowano:`
timestamp.

## What each sample demonstrates (brief.md Section 5 checklist)

Both samples:
- full August 2026 (31-day) month, ~10 fictional employees
  (`Pracownik 01`..`Pracownik 10`);
- at least one day of double-primary staffing — employees are generated
  in mirrored pairs (`01`/`02`, `03`/`04`, ...), so every working day for
  a pair is, by construction, a double-staffed day;
- `PLAN` and `WYK` sub-rows per employee;
- at least one urlop (leave) case and one chorobowe (sick) case, with
  the `WYK`-row hour summaries computed programmatically from the
  legend values shown, never hand-typed;
- one "correction" example (`Pracownik 09` day 21 on the 12h sample,
  `Pracownik 08` day 23 on the 24h sample) where `PLAN` and `WYK` show
  only the final, correct assignment — nothing on the printed page
  indicates a day was ever reassigned, per the owner's no-blame
  principle;
- header/provenance block: demo company/site name, real date range,
  fabricated `DEMO-SV-LINEAGE-*` schedule provenance, a `DEMO-REV-*`
  revision id, and a real generated-at timestamp;
- the full, owner-frozen legend (`D1..D5`, `N1..N5`, `U1..U5`,
  `C1..C5`), values un-normalized exactly as specified (e.g. `D4=2h` but
  `N4=24h` — the slot number does not carry a shared value across
  letters);
- grayscale-only visual encoding: `D`/`N`/`24` are distinguished purely
  by fill density (light → dark), `U` (urlop) by a solid border, `C`
  (chorobowe) by a dashed border — never by color/hue, so meaning
  survives a black-and-white photocopy.

`schedule_12h.pdf` additionally contains the brief's literal, binding
40h example (`Pracownik 05`, days 7–9): `PLAN` = `D1/D1/N2` = 40h,
`WYK` = `U1/U1/U2` = 40h — asserted in code (`render_samples.py`)
so the script fails loudly if the data is ever edited into breaking it.

`schedule_24h.pdf` additionally demonstrates a coordinator-configured
reserve slot: `U3` and `C3` are bound to `24h` for this sample only,
labelled `(konfiguracja demo)` in the legend — this is a demo
configuration, not a new default value for those slots.

## What this is NOT

- Not a production PDF generator, not wired into `rota/**`.
- Not reading any real Site/Employee/ScheduleVersion data.
- Not an editable document, not an XLSX, not an import path.
- Not a frozen visual contract — paper size, pagination, density, and
  every other visual choice here is a candidate for the owner to accept
  or reject (brief.md Section 15, item A15). Checkpoint B may not start
  until that acceptance is recorded.
