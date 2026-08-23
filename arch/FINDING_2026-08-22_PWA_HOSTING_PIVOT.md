# FINDING 2026-08-22 — PWA on Railway moved up from "after testing" to
"now"; real authentication required as a direct consequence. Reverses
two decisions made earlier the SAME session.

TASK: ROTA-T025 (scaffolded via task_init.py, HEAD e05dfb7 — repo-state
snapshot only, nothing implemented).

**UPDATE 2026-08-23** — Paweł raised the concrete threat directly: a
malicious actor reaching the Railway URL could impersonate a
coordinator through the front-end and tamper with schedules for fun —
framed explicitly as a data-security/RODO concern, not the T024
source-secrecy concern. This is real and worse than F1 below implied:
verified against current code today (`rota/application/bootstrap.py`,
`context.py`, `rota/domain.py`'s `Coordinator` class) — `coordinator_id`
is a caller-supplied string, trusted with ZERO verification anywhere in
`rota/`. There is no password/credential field on `Coordinator`, no
hash, no session concept, nothing. Today this is fine because the only
caller is a trusted local process; the instant a public HTTP layer
sits in front of this library (F2), ANY caller can pass any
`coordinator_id` and act as that coordinator with full write access —
there is no boundary to breach, because none exists yet to bypass.

**RODO angle, not previously captured in this document**: the data
this program holds is not merely operational. Employee imię/nazwisko
and full work schedule are ordinary personal data (RODO art. 6); L4/
zwolnienie lekarskie records (`AvailabilityKind.SICK_LEAVE`, already
schedule-based per T023) are health-adjacent and plausibly fall under
RODO art. 9's special category data, which carries a materially higher
compliance bar (stricter lawful-basis grounds, likely a DPIA, breach-
notification exposure) than a generic "keep the login secure" reading
of F1 suggests. This needs explicit owner/legal framing, not just an
engineering auth-scheme choice — flagging, not deciding, here.

**Consequence for sequencing** (previously an open question in this
same document, "Explicitly NOT decided here"): F1 (real authentication)
+ real per-action authorization (verifying the authenticated identity
actually owns the coordinator_id/site it's writing to on EVERY mutating
call, not just at login) must be a hard gate before any real coordinator
data — even test data resembling real employee names/schedules — ever
touches a public Railway URL. This does not have to block T021 UI-
screen-building work itself (which can proceed against a local/dev
backend), but it must block deployment to a publicly reachable URL.

STATUS: finding + direction, NOT a design doc, NOT frozen. Architect-
input material (same role as `arch/T004_T005_architect_brief.md`,
`arch/FINDING_2026-08-22_ABSENCE_HOURS_ACCOUNTING.md`,
`arch/FINDING_2026-08-22_DISTRIBUTION_PROTECTION.md`) — CC does not
design the hosting/auth architecture here; that's architect Claude's
job once Paweł relays this. This is the largest-scope finding of the
session — it reopens deployment architecture broadly, not just one
screen or one backend function.

## Origin
Paweł already has Railway provisioned for a planned PWA. Original
timeline: build the PWA AFTER the local-desktop testing phase. Revised
today: "PWA miało być po testach ale ja nie mam oporów by to zrobić od
razu." Real driver, stated explicitly: **a coordinator away from the
office needs the program to work on their phone when a plan needs an
immediate change** — this is a mobile-access requirement, not primarily
a distribution-protection or data-sharing motivation (those are real,
welcome side effects, not the origin).

Paweł's explicit scoping instruction: **"Wszystko co jest wymagane do
PWA a można zrobić teraz i nie wracać za miesiąc trzeba zrobić — i
logowanie do tego należy."** Do now, without deferring, everything
foundational a PWA needs to avoid rework later; login is explicitly
named as part of that foundational set.

## SUPERSEDED — two decisions made earlier this same session (2026-08-22)

**Deployment model**: `arch/T021_spec.md`'s "CROSS-CUTTING REQUIREMENT:
coordinator identity switcher" section recorded "deployment stays local
desktop app" (Continuity AI Tauri reuse, one local SQLite file per
install, `rota/application/store.py`). **SUPERSEDED** — moving to a
hosted PWA on Railway. `T021_spec.md` needs an explicit correction
pointing here, not left standing as if still current.

**Authentication**: the SAME section recorded "no password/login
subsystem exists or is being added now," grounded explicitly in
`rota/application/context.py`'s own docstring ("basic active-triple
check, not a new authorization subsystem") and the local-only, one-
computer-per-coordinator deployment. That grounding is gone the moment
the program is reachable from a phone over the internet — Paweł's own
earlier framing ("nikt dziś nie jest godny zaufania") applies with
equal force to remote access. **SUPERSEDED — real password-based
authentication is now required**, not deferred.

## What's foundational for PWA — do now (per Paweł's instruction)

**F1. Real authentication.** Password-based login, replacing the
no-password coordinator-identity-switcher plan. Existing
`Coordinator`/`CoordinatorSiteAssociation` data model stays useful (WHO
a coordinator is and WHICH sites they may access), but `context.py`'s
"basic active-triple check" needs an actual credential-verification
layer in front of it — does not exist anywhere in `rota/` today. Exact
scheme (password hashing, session/token mechanism, where credentials
live) NOT decided here.

**F2. A real hosted backend process.** Today's application layer
(`rota/application/*.py`) is a plain Python library of functions taking
an already-open `sqlite3.Connection` — no HTTP/API layer exists
anywhere. A Railway-hosted PWA needs a web API in front of this (REST/
GraphQL/whatever the architect picks) — this is new infrastructure, not
an extension of the Continuity AI Tauri-bridge pattern (NDJSON over a
local subprocess's stdin/stdout), which assumed a LOCAL Python process,
not a remote server. The bridge pattern from `continuity-ai` is likely
NOT reusable for this path — flag for the architect to confirm, don't
assume reuse just because it was the plan for the desktop path.

**F3. Database strategy for hosted, multi-access use.**
`store.py::open_store(db_path)` opens a bare local SQLite file path —
fine for one desktop install, not obviously fine for a hosted service
multiple coordinators hit concurrently over the network. Two candidate
directions, NEITHER decided here: (a) SQLite on a Railway persistent
volume, single service instance, minimal migration — but concurrent-
write behavior under real multi-user load needs real scrutiny, not
assumed fine; (b) migrate to Postgres (Railway's strength) — bigger
change, touches every `rota/persistence/*.py` module's SQL. This is a
significant, non-trivial architecture decision on its own.

**F4. Basic transport/hosting security** — HTTPS, environment/secrets
handling for whatever Railway deployment gets built. Standard, but
needs to be explicit in the eventual brief, not assumed.

## What can wait (PWA polish, not foundational)
- Full offline/service-worker caching, install-to-home-screen manifest
  polish, push notifications.
- Full mobile-first responsive redesign of all 9 T021 screens (the
  screens' DATA/ACTIONS from `arch/T021_spec.md` stay valid regardless
  of delivery shell — this is a layout/responsiveness pass, not a
  rebuild of screen logic).

## Impact on other in-flight findings

**T021** (`arch/T021_spec.md`): screen content/backend-function mapping
stays valid — none of it assumed a specific delivery shell. The
"coordinator identity switcher" section needs correcting to point here
instead of describing a no-password picker. Delivery target changes
from a Tauri desktop artboard set to a responsive web app — a frontend
concern for whoever builds the actual screens, not a re-spec.

**T024** (`arch/FINDING_2026-08-22_DISTRIBUTION_PROTECTION.md`,
distribution protection): largely SIMPLIFIED, not invalidated. If
testers only ever receive a URL (hosted backend + PWA frontend), L2
("ship a compiled build, not source") is satisfied automatically —
there is no local backend folder to copy at all. L1 (NDA) is unchanged,
still needed regardless of hosting model. L3 (time-limited test
builds) becomes a server-side account-expiry concern instead of a
client-side build-expiry trick — likely easier to implement correctly
hosted. L4 (watermark) still applies, similarly easier server-side.
T024's document should be revisited once T025's architecture is decided
— not rewritten yet, since the hosting decision itself isn't final
here.

## Explicitly NOT decided here
- Exact auth scheme (password hashing, sessions vs. tokens, password
  reset, whether `Coordinator` gets a new credential field or a
  separate credentials table).
- Web API framework/shape for F2.
- SQLite-on-volume vs. Postgres for F3.
- Whether the existing `continuity-ai` Tauri shell gets dropped entirely
  for this path or kept as a possible future native-app option
  alongside the PWA.
- Timeline/sequencing relative to T021's own UI screen-building work —
  Paweł has not yet said whether T025's foundational pieces (F1-F4)
  block T021 implementation from starting, run in parallel, or come
  first.

## Next step
This is architecture-decision scale, larger than a normal Task —
needs real architect engagement (own brief, own review), not something
CC should design unilaterally. Not implemented, not designed in detail,
here.
