# DATA STATUS — what the data in this repo and in the running instance actually is

STATUS: statement of fact about data provenance. Binding for how every
other document here must be read. If any other document contradicts
this one, this one is correct and the other one is a defect to fix.

## 1. There is no third-party data anywhere in this project

- No real personal data of any real employee has ever been entered,
  imported, or processed. This matches the frozen product spec
  (`ELNATH_WARD_HANDOFF_FINAL_2026-08-10/02_..._SPEC_PRODUKTOWA_v0.19`:
  *"W fazie projektowania i budowy nie używamy prawdziwych danych
  osobowych."*) and `arch/FINDING_2026-08-23_RODO_INTERNAL_NETWORK_
  BASELINE.md` (*"persisted data is test data, not real client data"*).
- **Elnath Rota has no customer.** No company has supplied data, been
  given access, run a pilot, or entered into any engagement. Nothing in
  this repo documents work performed for a third party.
- Every employee, shift demand, availability record, target and schedule
  in the system was created by the owner for testing.

## 2. The site names are borrowed; the data under them is not

Two site objects appear throughout `arch/FINDING_*`:

| Site | Where the name comes from | The data |
|---|---|---|
| **Bolf** | A company the owner once worked at | Entirely synthetic, created by the owner |
| **Royal** | Probably the name of some existing company; no connection to this project | Entirely synthetic, created by the owner |

The names were chosen because a recognisable name is easier to reason
about than `SITE-c9aebae1ba...`. **Neither company has any relationship
with this project**, has supplied anything, or is aware of it. Any
resemblance between a stored schedule and either company's actual
operations is coincidental.

Renaming both sites to obviously fictional names is worth doing before
any external reader sees the system; it is not done yet, which is why
this file exists.

## 3. Two words that were used loosely, and what they mean here

Documents written on 2026-09-20 and 2026-09-21 use "real" and
"production" in a narrow technical sense that an outside reader will
misread. Their intended meaning:

**"production" / "production read"** = *a read against the owner's own
running Rota instance*, i.e. the live application database rather than a
test database. It does **not** mean a customer's system and it does
**not** mean real personal data. There is no customer system to read.

**"real object"** (as in "real object Bolf", "real Royal") = *a complete
site object assembled from the application database through the
production code path* (`assemble_planning_state`), as opposed to a
hand-built minimal `PlanningState` fixture in `tests/support/`. The
distinction is about **how complete and how realistically assembled the
object is**, not about the data being non-synthetic. This distinction
carries real weight in those findings: several defects only appear on a
fully assembled object and vanish on a toy fixture, which is precisely
what made them worth recording.

Both words remain in the older documents where deleting them would
damage the finding's technical meaning. They are to be read as defined
above.

## 4. What this means for anyone evaluating this repo

The findings in `arch/` are genuine investigation results — reproducible
experiments, including ones that failed to confirm their own hypothesis.
What they are **not** is evidence of a deployment serving a real
organisation, and nothing here should be presented as such.

## 5. New documents

Do not write "real data", "production data", "real customer" or
"owner-approved production reads" in new documents. Write "the running
instance", "stored synthetic data", or "a fully assembled site object",
and say plainly that the data is synthetic.
