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

## UPDATE 2026-08-23 — reusable encryption-at-rest code exists (LynxMask-Desktop)

Paweł: an existing separate project, `LynxMask-Desktop`
(`C:\Users\p_pie\Desktop\LynxMask-Desktop`, also on GitHub), already has
production encryption code that can be viewed/copied. Reviewed the two
relevant modules:

- `backend/anonymizer_crypto.py` — AES-256-GCM (via `cryptography.hazmat`)
  for whole-blob encryption of a JSON map, plus a keystore for the 32-byte
  ENC/MAC key pair protected by Windows DPAPI (`CryptProtectData`/
  `CryptUnprotectData`), with a non-Windows fallback (plain file, 0600
  permissions, explicitly logged as weaker). Per-entry HMAC-SHA256 signing
  (`sign_entry`/`verify_entry`) detects tampering of individual records
  independent of the whole-blob AEAD tag.
- `backend/crypto_selftest.py` — 22 in-memory adversarial tests (roundtrip,
  wrong key, tampered ciphertext, wrong/truncated header, nonce
  uniqueness, MAC tamper detection, plaintext-not-in-blob) with no disk/
  DPAPI dependency — a genuine correctness self-test, reusable as a
  pattern regardless of what gets encrypted.

### What transfers directly to Rota

**The key-management layer (DPAPI keystore, key generation, key
lifecycle)** transfers essentially as-is — it solves "where does the
encryption key live and how is it protected from other Windows accounts,"
which is orthogonal to what's being encrypted. This is real, tested,
already-adversarially-audited code, not something to reinvent.

### What does NOT transfer directly

LynxMask's `encrypt_map`/`decrypt_map` pattern encrypts one JSON blob as a
single AEAD unit — read the whole file, decrypt, use; re-encrypt the
whole thing on write. That fits a map file. It does **not** fit Rota's
`rota/persistence/db.py` SQLite store as-is: the product needs live,
indexed, partial reads/writes (a single ScheduleVersion, a single
Assignment row) against a database that can grow large, not "decrypt the
entire file into memory on every open." Applying the same whole-blob
approach to the live SQLite file would mean holding the entire decrypted
database in memory for the process lifetime and serializing/re-encrypting
on every write — a correctness and performance regression, not a security
upgrade.

### Candidate directions for Rota specifically (not decided here)

1. **SQLCipher** (transparent page-level AES encryption, drop-in
   replacement for the stdlib `sqlite3` connection) — the standard answer
   for "encrypt an entire live SQLite database" without changing query/
   access patterns. Would still need the LynxMask-style DPAPI keystore to
   protect the SQLCipher passphrase.
2. **Field-level encryption** of specific sensitive columns (employee
   names, L4/absence records) using LynxMask's own AES-256-GCM primitives
   directly, keyed via the same DPAPI keystore pattern — closer to a
   direct code port, but needs new columns/migration work and changes how
   those fields are queried (no more `WHERE display_name = ?`).
3. **Filesystem/OS-level encryption** (BitLocker etc.) — simplest, but
   it's a deployment/ops decision outside the product, not something the
   application enforces itself, and doesn't protect against a
   authenticated-but-malicious local user reading the file directly.

The per-entry HMAC pattern is also worth keeping in mind separately: it's
a good fit for adding tamper-evidence to `coordinator_action_records`
specifically (Rota's SQL triggers already make it append-only/immutable
at the query layer, but they don't stop someone editing the raw `.db`
file directly outside the application — an HMAC per action row would
close that specific gap, independent of whichever storage-encryption
direction is chosen above).

## RULING 2026-08-23 — sequencing: not a T021 blocker

Paweł asked whether SQLCipher work must precede T021 (frontend). Ruling:
**no**. SQLCipher is a swap at `rota/persistence/db.py`'s `connect()`
only — it changes no function signature or business logic anything in
`rota/application/*.py` (and therefore T021's screens) calls. Today's
persisted data is test data, not real client data. Same sequencing
logic as F1 (real authentication) in
`arch/FINDING_2026-08-22_PWA_HOSTING_PIVOT.md`: this does not block
T021 UI-screen-building work, but it (together with F1) becomes a hard
gate before any real client employee data is ever loaded, regardless
of deployment path (on-premise or Railway/PWA).

## Explicitly NOT decided here

- Exact mechanism for encryption-at-rest (SQLCipher vs. field-level vs.
  filesystem/OS-level) — direction only, per the UPDATE above.
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
