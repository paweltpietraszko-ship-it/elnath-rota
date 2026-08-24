# FINDING 2026-08-22 — distribution protection: ship a built app, not the
source folder, before any tester ever receives the program.

**UPDATE (same day)**: `arch/FINDING_2026-08-22_PWA_HOSTING_PIVOT.md`
(ROTA-T025) moved the deployment target to a hosted PWA on Railway. If
that lands, L2 below (compile/package a local build) is satisfied
automatically — testers would only ever receive a URL, no local backend
folder to copy at all. This document's content stays valid as a
fallback/reference if a local desktop build ever ships too, but L2's
priority drops once T025 is real. L1 (NDA) is unaffected either way.

TASK: ROTA-T024 (scaffolded via task_init.py, HEAD e05dfb7 — repo-state
snapshot only, no implementation started).

STATUS: finding + direction, NOT a design doc, NOT frozen. Architect-
input material (same role as `arch/T004_T005_architect_brief.md` and
`arch/FINDING_2026-08-22_ABSENCE_HOURS_ACCOUNTING.md`) — CC does not
author the implementation brief here; that's architect Claude's job
once Paweł relays this.

## Origin / requirement
Paweł: giving testers a plain copy of the project folder must not hand
them a working, readable copy of the program. Not defending a trade
secret against sophisticated reverse-engineering — defending against
the trivial "copy/paste the folder" case specifically. Confirmed scope:
**a compiled/packaged application without source is sufficient** — no
request for stronger DRM, license servers, or code obfuscation beyond
that baseline.

## GATE, not a priority-before-T021 item
Unlike ROTA-T023 (correctness-affecting, explicitly ordered before
T021), this is a **release gate**: it blocks the moment any build is
handed to an external tester, not the start of T021 implementation
work. T021 UI implementation can proceed in parallel; this only needs
to be solved before the FIRST external handoff.

## Current state (checked 2026-08-22)
No packaging/build tooling exists in this repo yet — no
PyInstaller/Nuitka spec, no `tauri.conf.*`, nothing (`find` came back
empty). The desktop shell itself (Tauri + Rust↔Python bridge) is a
REUSE/ADAPT target from a separate repo, `continuity-ai`
(`arch/spec.md` §"REUSE/ADAPT: Continuity AI desktop shell"), not yet
pulled into this repo. Packaging work has no existing foundation to
extend — it starts from nothing.

## Layers, in priority order (Paweł's framing: legal first, technical second)

**L1. Written testing/NDA agreement** — the actual enforceable
protection (real legal consequence, not a technical speed bump). NOT
CC's job to draft the binding text — flag that a lawyer should produce/
review it. Should cover at minimum: no copying/redistribution of the
software or its source, no reverse-engineering, confidentiality of
anything observed during testing, and what happens to any local copy
at the end of the test period.

**L2. Ship a packaged/compiled build, never the source folder** —
confirmed sufficient by Paweł. For this stack specifically: Tauri
already compiles its own Rust/frontend shell to a binary; the LOCAL
PYTHON BACKEND is the part that would otherwise ship as plain, readable
`.py` files inside that install — needs compiling (Nuitka or
PyInstaller, either produces a binary instead of `.py` source) as part
of the build/packaging step, not the dev/test workflow. This alone
defeats "copy the folder, have the source."

**L3. Time-limited test builds** — a build stops functioning after a
fixed number of days from build time. No server/network dependency
(consistent with the earlier "no network access point right now"
decision from the coordinator-identity-switcher discussion) — a local,
offline check. Appropriate specifically for a bounded testing phase,
not a mechanism meant to survive into a real paid release.

**L4. Per-tester watermark** — embed a tester-specific identifier
somewhere low-friction (e.g. the PDF export's footer, or an
about/diagnostics screen) so a leak is traceable to its source. Does
not prevent copying, purely a deterrent/accountability measure.

## Explicitly NOT proposed
- A license-activation SERVER (would reopen the "no network access
  point" question settled during the coordinator-identity-switcher
  discussion — a separate decision if ever wanted, not bundled into
  this finding).
- Obfuscation beyond plain compilation (PyArmor-style bytecode
  obfuscation, anti-debugging, etc.) — Paweł's stated bar is "no
  source, not maximum resistance to a determined reverse-engineer."

## Explicitly NOT decided here
- Exact packaging toolchain (Nuitka vs. PyInstaller vs. something
  else) — a build-engineering choice, not made here.
- Exact expiry mechanism/duration for L3.
- Where/how L4's watermark is embedded and generated per tester.
- Whether this becomes its own implementation round on `task/ROTA-T024`
  or folds into whichever task first produces an actual distributable
  build.

## Next step
Needs architect input (own brief, own review) before any packaging
code is written — this is release-engineering, not domain logic, so it
may not need the same Codex-heavy correctness gate T023 needed, but
still needs a real decision on toolchain/sequencing before CC builds
anything. Not implemented, not designed in detail, here.
