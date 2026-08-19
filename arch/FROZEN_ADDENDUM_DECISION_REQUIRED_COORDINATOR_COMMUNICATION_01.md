# FROZEN PRODUCT CONTRACT ADDENDUM — DECISION-REQUIRED-COMMUNICATION-01

ADDENDUM_ID: DECISION-REQUIRED-COMMUNICATION-01
DATE: 2026-08-19
STATUS: FROZEN_PRODUCT_CONTRACT_ADDENDUM
BASE_SHA: 5b35e3225f546bc7763c51b34e8a7ebe77553b58
OWNER_DECISION_SOURCE: arch/T013_solver_communication_architect_brief.md
DEPENDS_ON: T012 + T016 + T018 merged on main

## SUPERSESSION — EXACT SCOPE

Ten addendum superseduje wyłącznie dotychczasową, statyczną i techniczną treść końcowego `DECISION_REQUIRED`:
- wartości `Blocker.condition` pokazywane koordynatorowi;
- wartości `DecisionRequiredPayload.unblocking_options`.

Nie zmienia struktury `PlanningResult`, `DecisionRequiredPayload`, `Blocker`, `BlockingDemand` ani `LoadBlocker`.

Nie zmienia żadnej reguły planowania, HARD/SOFT, solvera, validatora, persistence ani lifecycle.

W szczególności NIE zmienia:
- T018 literalnej kolejności automatycznych prób: NORMAL capped -> DAY_ONLY fallback capped -> DAY_ONLY + T012 emergency 24h capped -> uncapped LOAD diagnosis;
- zasady, że DAY_ONLY pozostaje HARD w normalnym pass i może być użyty dopiero w istniejącym T018 fallbacku;
- T012 emergency-24h semantics ani provenance;
- LOAD-01, REST-01, availability, SiteRule, membership ani coverage semantics;
- statusów FEASIBLE / DECISION_REQUIRED / TECHNICAL_ERROR.

## FINAL-OUTCOME BOUNDARY

Koordynator widzi wyłącznie:
1. kompletny poprawny grafik (`FEASIBLE`), albo
2. końcowe `DECISION_REQUIRED`, kiedy wszystkie automatyczne próby dopuszczone aktualnym kontraktem zostały wyczerpane.

Etapy pośrednie solvera są wewnętrzne. Nie wolno ich przedstawiać jako opcji, komunikatów ani części decyzji koordynatora.

T013 nie może emitować komunikatu po Stage 1 albo Stage 2 T018, jeżeli engine ma jeszcze wykonać kolejny automatyczny fallback.

TECHNICAL_ERROR pozostaje technical failure. T013 nie tłumaczy go na decyzję koordynatora ani nie uruchamia dalszej próby.

## ARCHITECTURAL OWNER — ONE PURE GUIDANCE BUILDER

Końcowy coordinator-facing payload ma jednego pure ownera w planning layer, bez I/O i bez persistence.

Dozwolony kształt: nowy wąski moduł `rota/planning/decision_guidance.py`, który:
- konsumuje fakty diagnostyczne już policzone przez engine/solver/validator;
- filtruje i renderuje końcowe `Blocker`;
- wylicza dynamiczne `unblocking_options`;
- zwraca istniejący `DecisionRequiredPayload`.

Nie tworzyć:
- nowego DTO równoległego do `DecisionRequiredPayload`;
- command bus / mediator / workflow / event bus;
- drugiego solvera;
- rekurencyjnego `plan()` do budowania tekstu;
- publicznego `ignore_hard` ani nowych override flags;
- persistence dla komunikatu.

`rota/planning/engine.py` nadal decyduje, KTÓRY finalny autonomy boundary zaszedł. Guidance builder jedynie przekształca jego finalne fakty w komunikat dla koordynatora.

## RAW DIAGNOSTICS REMAIN INTERNAL

`SolverOutcome.unassignable_reasons`, `site_rule_exclusions`, `ViolationDetail.rule` i inne techniczne kody pozostają wewnętrznymi faktami planowania.

Nie zmieniać ich znaczenia tylko po to, aby uzyskać tekst UI.

Coordinator-facing `Blocker.condition` powstaje dopiero na granicy końcowego payloadu.

## COORDINATOR BLOCKER TEXT — EXACT OWNER MAPPINGS

Dla wbudowanych kodów coordinator-facing `Blocker.condition` ma dokładnie:

| Raw condition | Coordinator condition |
|---|---|
| `UNAVAILABLE-01` | `Koliduje z checkbox: Ogólna dostępność` |
| `DAY_ONLY-01` | `Koliduje z checkbox: Nocka` |
| `SICK_LEAVE-01` | `Koliduje z zapisem: Chorobowe` |
| `LEAVE_GRANTED-01` | `Koliduje z zapisem: Urlop` |
| `REST-01` | `Koliduje z odpoczynkiem dobowym` |
| `LOAD-01` | `Koliduje z tygodniowym czasem pracy` |
| `EXTERNAL-01` | `Wsparcie zewnętrzne` |
| `EXTERNAL_SUPPORT_DISABLED` | `Wsparcie zewnętrzne` |
| `SHIFT-24-01` | `Koliduje z checkbox: 24` |
| `DAY_SHIFT_OFF-01` | pozostaje literalnie `DAY_SHIFT_OFF-01` do osobnej decyzji właściciela |

`SHIFT-24-01` używa nazwy Panelu Sterowania `24`; T013 nie wprowadza alternatywnego określenia kwalifikacji.

## MEMBERSHIP IS INVISIBLE

Raw `MEMBERSHIP_DISABLED` i `MEMBERSHIP-01`:
- mogą nadal istnieć wewnętrznie;
- nie tworzą coordinator-facing `Blocker`;
- nie tworzą `unblocking_option`;
- nie mogą spowodować sugestii automatycznego dodania konkretnego pracownika do obsady.

Tylko koordynator decyduje, kto należy do bieżącej obsady.

`EMP-02` nie jest częścią T013 — został wycofany przez T016 i nie może wrócić przez warstwę komunikacji.

## INTERNAL COVERAGE MARKERS ARE NOT USER CODES

`INSUFFICIENT_COVERAGE`, `UNKNOWN` i równoważne solver-only markery nie są coordinator-facing condition codes.

Nie pokazuje się ich jako `Blocker.condition`.

Jeżeli po odfiltrowaniu technicznych/ukrytych przyczyn nie istnieje żadna konkretna akcja, coordinator dostaje końcową informację o braku automatycznego rozwiązania, a nie pustą statyczną listę technicznych kodów.

## SITE RULE DESCRIPTION — NEVER rule_version_id

Jeżeli raw condition jest dokładnym `SiteRuleVersion.rule_version_id` obecnym w `PlanningState.site_rules`, coordinator nie widzi tego identyfikatora.

Coordinator-facing `Blocker.condition`:
- używa `SiteRuleVersion.description.strip()` gdy opis istnieje i nie jest pusty;
- jeśli `description` jest `None` albo pusty, używa dokładnie `Koliduje z zapisaną regułą obiektu`;
- nigdy nie używa `rule_version_id` jako fallbacku tekstowego.

Lookup jest pure po `PlanningState.site_rules`; żadnego repository/application I/O w guidance builderze.

Raw `rule_version_id` pozostaje wewnętrzną provenance tam, gdzie już istnieje w planowaniu/persistence.

## DYNAMIC UNBLOCKING OPTIONS — ARCHITECT TECHNICAL CHOICE

T013 wybiera evidence-backed guidance zamiast drugiego counterfactual solvera.

`unblocking_options` NIE są już stałą listą per `_decision_for_*`.

Opcja może powstać tylko z:
- raw blockera obecnego w tym konkretnym końcowym diagnosis, albo
- finalnego faktu specyficznego dla danej autonomy-boundary path (np. frozen Assignment albo `load_blocker`).

Nie ma opcji „na wszelki wypadek”. Brak raw przyczyny oznacza brak odpowiadającej jej opcji.

Ta technika wskazuje konkretną decyzję, która adresuje realnie wykrytą przeszkodę. Nie jest obietnicą, że pojedyncza decyzja sama w sobie gwarantuje FEASIBLE; po zmianie wejścia zwykły PLAN ponownie wykonuje pełny aktualny kontrakt.

## ACTION FAMILIES / WORDING

Opcje są grupowane per action family i deduplikowane. Dla employee-scoped action używać `Employee.display_name`; przy braku rekordu dopuszczalny jest `employee_id` jako techniczny fallback danych, nie jako nazwa reguły.

Dozwolone coordinator-facing templates:

- raw `UNAVAILABLE-01` -> `Zmień Ogólna dostępność: <lista pracowników>`;
- raw `DAY_ONLY-01` -> `Zmień Nocka: <lista pracowników>`;
- raw `SHIFT-24-01` -> `Zmień 24: <lista pracowników>`;
- raw `EXTERNAL-01` / `EXTERNAL_SUPPORT_DISABLED` -> `Skonfiguruj Wsparcie zewnętrzne: <lista pracowników>`;
- raw `SICK_LEAVE-01` -> `Ręczna korekta mimo zapisu Chorobowe zgodnie z kontraktem: <lista pracowników>`;
- raw `LEAVE_GRANTED-01` -> `Ręczna korekta mimo zapisu Urlop zgodnie z kontraktem: <lista pracowników>`;
- raw `REST-01` -> `Ręczna korekta z uwzględnieniem odpoczynku dobowego zgodnie z kontraktem: <lista pracowników>`;
- raw SiteRule -> `Zmień zapisaną regułę: <coordinator condition z opisu SiteRule>`;
- finalny frozen-Assignment autonomy boundary -> `Odmroź zapisane przypisania i uruchom planowanie ponownie`;
- finalny `load_blocker` -> `Świadomie zaakceptuj przekroczenie tygodniowego czasu pracy`.

`DAY_SHIFT_OFF-01` nie generuje własnej nowej opcji T013, bo właściciel odłożył decyzję o znaczeniu/nazwie tej reguły w Panelu Sterowania.

Membership codes nie generują opcji.

T013 nie tworzy opcji „dodaj <pracownik> do obsady” na podstawie `MEMBERSHIP-01`/`MEMBERSHIP_DISABLED`.

## EXTERNAL SUPPORT — HUMAN, NOT X/Y

Tekst `potwierdzenie X/Y` znika z coordinator-facing payloadu.

Wsparcie zewnętrzne używa wyłącznie nazwy `Wsparcie zewnętrzne`.

Opcja jest dynamiczna: pojawia się tylko wtedy, gdy finalne raw diagnosis zawiera `EXTERNAL-01` albo `EXTERNAL_SUPPORT_DISABLED` dla istniejącego kandydata przechodzącego przez ścieżkę EXTERNAL_SUPPORT.

T013 nie inventuje nowego pracownika, membership ani ExternalSupportWindow i niczego nie zapisuje automatycznie.

## DAY_ONLY AFTER T018 — NO REGRESSION

Coordinator-facing opcja `Zmień Nocka` może pojawić się wyłącznie w KOŃCOWYM `DECISION_REQUIRED`.

Nie wolno proponować jej po normalnym Stage 1, jeżeli T018 ma jeszcze wykonać istniejący DAY_ONLY fallback.

Nie wolno zmieniać istniejącej autoryzacji `EMPLOYEE_DAY_ONLY_N_EXCEPTION`, canonical provenance ani exceptional_n minimization.

T013 tylko komunikuje finalny blocker, który pozostał po wyczerpaniu automatycznych prób.

## FOUR PATHS — ONE POLICY

Ta sama polityka coordinator-facing obowiązuje wszystkie cztery autonomy-boundary paths:
1. `_decision_for_unassignable`;
2. `_decision_for_conflict`;
3. `_decision_for_conflicts`;
4. `_load_decision` (wraz z `_decision_for_load` jako istniejącym wrapperem uncapped candidate).

Żadna ścieżka nie ma własnej statycznej listy tekstów po T013.

## EMPTY-ACTION FALLBACK

Jeżeli finalny `DECISION_REQUIRED` ma realne blocking demands/facts, ale po zastosowaniu powyższych reguł nie ma żadnej coordinator-action, `unblocking_options` zawiera dokładnie jeden tekst:

`Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach.`

Nie używać pustej listy do zakomunikowania tego stanu i nie ujawniać zamiast niej membership/technical markers.

## DETERMINISM / DEDUP

Coordinator-facing blockers:
- zachowują `employee_id` w istniejącym polu strukturalnym;
- deduplikują identyczne `(employee_id, rendered_condition)`;
- mają stabilną kolejność niezależną od wejściowej kolejności tych samych raw faktów.

Opcje:
- jedna opcja per action family / SiteRule description;
- employee names unique i deterministycznie posortowane;
- identyczny PlanningState + final diagnosis daje identyczne `unblocking_options`.

Kolejność action families jest techniczna i stabilna:
1. Ogólna dostępność;
2. Nocka;
3. 24;
4. Wsparcie zewnętrzne;
5. Chorobowe;
6. Urlop;
7. odpoczynek dobowy;
8. zapisane SiteRule descriptions;
9. odmrożenie;
10. tygodniowy czas pracy;
11. empty-action fallback.

## NO SPEC / LOCK REWRITE

Nie edytować `arch/spec.md` ani `arch/FROZEN.lock` w T013.

Ten addendum superseduje wyłącznie coordinator-facing treść końcowego `DECISION_REQUIRED`; frozen execution/planning semantics pozostają bez zmian.
