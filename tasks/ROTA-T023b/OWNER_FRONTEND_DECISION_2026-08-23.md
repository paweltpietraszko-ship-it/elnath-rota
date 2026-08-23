# ROTA-T023b — OWNER DECISION: SITE CREATION AND REGIME CORRECTION

STATUS: BINDING OWNER DECISION — ARCHITECT MUST CONSOLIDATE BEFORE CC IMPLEMENTATION
DATE: 2026-08-23
APPLIES TO: ROTA-T023b backend contract and the T021 frontend that creates/edits a Site

This note records product decisions made after contract HEAD `d6009df1570265edfa213a956e315bc0b55ffa2c`.
It supersedes conflicting statements in that draft. It is not permission for CC to infer missing architecture; the architect must fold these decisions into one final T023b contract before implementation.

## 1. NO REGIME CHECKBOX IN A GENERIC SITE FORM

`planning_regime` is a fundamental Site classification, not an optional checkbox or an ordinary editable setting.

The frontend must not expose one generic Site-creation form with an `OCHRONA` on/off checkbox, toggle or ordinary dropdown. That interaction makes accidental `ORDINARY` classification too easy.

Instead, creation starts from separate, unambiguous entry points/screens, at minimum:

- create an OCHRONA Site;
- create an ORDINARY Site.

SPRZATANIE is also a distinct service flow in the product direction, including its future rules concerning employees with disabilities. T023b must not invent or implement those rules. The frontend architecture must nevertheless avoid treating SPRZATANIE as `ORDINARY` merely because T023b does not implement it yet.

The selected creation flow supplies the Site classification. A new real Site must never become `ORDINARY` merely because a field was omitted or a UI default was accepted. Migration compatibility for existing test data is a separate technical concern and must not become the creation default for new Sites.

## 2. SEPARATE USER FLOWS, SHARED IMPLEMENTATION

Separate screens do not authorize three copies of the same application logic.

Common fields, validation, components and persistence should be shared. The user-facing creation entry point determines the regime and exposes only the fields/rules relevant to that service. CC must not duplicate repositories, Site models or common form logic per service.

After creation, the Site's service classification must remain clearly visible in its workspace. Ordinary Site editing must not contain a control that changes `planning_regime`.

## 3. CORRECTING A CREATION MISTAKE BELONGS TO T023b

Preventing an accidental ordinary edit does not mean that a mistaken initial classification can never be repaired.

T023b must include a separate, deliberate and audited correction operation. It is not a checkbox in `update_site`, and it is not deferred to an unspecified future task. The correction UX must be visibly distinct from ordinary editing and require explicit confirmation.

Historical ScheduleVersions and REALIZED Assignments are immutable facts. Correcting the Site classification must not rewrite performed work or retroactively modify those records. New planning after the correction uses the corrected Site classification.

The architect must specify the minimum backend command, authorization, audit fact and treatment of any not-yet-realized current plan. CC must not invent those missing mechanics from this note.

## 4. REQUIRED CONTRACT FOLLOW-UP

Before CC implementation, the architect must update the frozen addendum and task brief so that they:

1. remove the generic-checkbox implication;
2. remove the claim that correction is outside T023b;
3. keep ordinary editing unable to change the regime;
4. include the deliberate audited correction operation in T023b scope;
5. preserve historical/REALIZED schedule facts;
6. bind the later T021 frontend to the separate-entry-point rule without duplicating shared implementation.
