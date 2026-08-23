# FINDING 2026-08-23 — RODO baseline for client-owned data, internal-network
deployment: what applies regardless of internet exposure, and what's the
vendor's (Paweł's) legal position vs. the client's.

STATUS: finding + direction, NOT a design doc, NOT frozen. Architect-input
material (same role as `arch/FINDING_2026-08-22_PWA_HOSTING_PIVOT.md`,
`arch/FINDING_2026-08-22_DISTRIBUTION_PROTECTION.md`) — CC does not decide
the technical security architecture here; that's for the architect/owner
once this is relayed. Web-researched 2026-08-23, not answered from prior
knowledge, given real legal-exposure stakes.

## Origin / question

Paweł: the client owns the protected personal data (data controller), but
"musimy zabezpieczać dane zgodnie z prawem" (we still must secure it per
law) — what are the current legal requirements for a program that
processes personal data but never makes it available outside the client's
own corporate network?

## Core finding: network exposure does not gate RODO applicability

RODO's definition of "przetwarzanie" (processing) — storage, use, access,
etc. — applies the moment personal data touches the system, regardless of
whether that data ever leaves the client's internal network. An
internal-network-only deployment does not exempt the program from RODO;
it only removes the international-transfer question (Schrems II / SCCs /
adequacy decisions) that applied to the earlier Railway/PWA hosting
discussion (`arch/FINDING_2026-08-22_PWA_HOSTING_PIVOT.md`).

## Who is legally bound: administrator/processor roles, not the vendor by default

RODO art. 25 (privacy by design/by default) and art. 32 (security of
processing) formally bind the **administrator** (data controller) and the
**podmiot przetwarzający** (processor — someone who actually processes
data on the administrator's behalf). A pure software vendor who:

- ships software that runs entirely on the client's own infrastructure, and
- never has access to the client's live/production personal data (no
  remote support that touches real data, no telemetry, no data sent back
  to the vendor for backup/diagnostics),

is **neither** administrator nor processor under RODO. In that
configuration, formal RODO compliance responsibility rests entirely with
the client. No art. 28 data processing agreement (umowa powierzenia) is
required between Paweł and the client under this configuration.

**This status is fragile and binary, not a spectrum**: the moment the
vendor touches the client's real data even once (remote diagnostics on a
live database, a support session that reads real records, telemetry that
includes personal data), vendor status flips to processor and a
`Data Processing Agreement` becomes legally required. This is worth
naming explicitly in whatever agreement governs delivery/support, so
support practices don't accidentally create undocumented processor status.

## Why "not legally bound" is not "nothing to do"

Even without a direct RODO duty, two independent pressures remain:

1. **Contractual/civil liability**: if a client suffers a data breach
   traceable to a defect in the delivered software (e.g., no
   authentication, unencrypted storage), the client faces the RODO
   penalty, but the vendor can face separate civil/contractual liability
   (rękojmia, odszkodowanie za wadliwe wykonanie) plus reputational risk,
   independent of who UODO fines.
2. **Market/professional expectation**: privacy-by-design (art. 25) is
   the industry-standard baseline EDPB and UODO both actively promote to
   software developers specifically (UODO has run seminars targeted at
   programmers on exactly this topic) — not a formal vendor obligation,
   but the de facto bar a competent security-industry software product
   is expected to clear.

## Concrete art. 32 measures relevant to THIS product, independent of network exposure

1. **Access control / real authentication** — same finding as F1 in
   `arch/FINDING_2026-08-22_PWA_HOSTING_PIVOT.md`, and it stays load-bearing
   here too: "it's an internal network" does not excuse "no login," since
   art. 32 access-control duties don't reference network topology.
2. **Encryption at rest** — the SQLite store file is not currently
   encrypted. Worth deciding on for the frontend/deployment architecture.
3. **Encryption in transit (TLS)** — increasingly expected even for
   internal-network traffic; "it's just the local network" is a weakening
   justification in current audit practice, not a settled exemption.
4. **Audit logging of coordinator actions** — already exists
   (`CoordinatorActionKind` / `site_memory`), supports the accountability
   expectation directly.
5. **Backups / availability recovery** — already exists
   (`rota/application/backup.py`).
6. **Data minimization** — collect/retain only what the product actually
   needs.
7. **L4/sick-leave data** (`AvailabilityKind.SICK_LEAVE`, already
   schedule-based per T023) is plausibly RODO art. 9 special-category
   (health) data — see `arch/FINDING_2026-08-22_PWA_HOSTING_PIVOT.md`'s
   earlier note. The client's DPIA/legal-basis obligation is theirs, but
   this raises the bar for how carefully this specific data should be
   handled technically in the product (e.g., candidate for encryption-at-
   rest priority, tighter access-control scoping).

## Sources (web-researched 2026-08-23)

- GDPR.pl, art. 32 interactive text and commentary
  (https://gdpr.pl/baza-wiedzy/akty-prawne/interaktywny-tekst-gdpr/artykul-32-bezpieczenstwo-przetwarzania)
- RPMS Kancelaria, practical rules for art. 32 IT processing
  (https://rpms.pl/praktyczne-zasady-przetwarzania-danych-osobowych-w-sposob-teleinformatyczny-art-32-rodo/)
- poradyodo.pl, vendor/service-provider RODO role distinctions
  (https://www.poradyodo.pl/temat-tygodnia/serwis-sprzetu-komputerowego-i-oprogramowania-w-swietle-rodo-jak-uregulowac-wspolprace-z-serwisantem-9435.html)
- LexDigital / Maniszewska / rodogrupa.pl, privacy by design (art. 25) and
  EDPB Guideline 4/2019 commentary
  (https://lexdigital.pl/privacy-by-design/, https://maniszewska.pl/en/privacy-by-design-by-default-gdpr-guide/)

## Explicitly NOT decided here

- Whether encryption-at-rest for the SQLite store is actually implemented,
  and with what mechanism (SQLCipher vs. filesystem/OS-level encryption
  vs. something else).
- Whether TLS is required for the internal-network deployment path
  specifically (vs. the already-settled Railway/PWA path, which needs it
  regardless as a public-internet service).
- The exact contractual language confirming Paweł has no standing access
  to client production data (a legal-drafting question, not CC's job).
- Whether/how this changes T024 (distribution protection) or T025 (PWA
  hosting) — those findings stay valid; this document adds the
  internal-network-only case as an additional, not replacing, deployment
  scenario.

## Next step

Architect input material only. Needs real architect/owner engagement to
decide which of the concrete measures above become actual T021/T025
implementation requirements, and in what priority relative to the
Railway/PWA path already in flight. Not implemented, not designed in
detail, here.
