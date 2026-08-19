# FROZEN PRODUCT CONTRACT CLARIFICATION — DAY-ONLY-N-FALLBACK-01 R1

CLARIFICATION_ID: DAY-ONLY-N-FALLBACK-01-R1
DATE: 2026-08-19
STATUS: FROZEN_PRODUCT_CONTRACT_CLARIFICATION
BASE_ADDENDUM: arch/FROZEN_ADDENDUM_DAY_ONLY_N_FALLBACK_01.md
SOURCE_FINDING: T018-R1-2

## EXACT SCOPE

Ta clarification zamyka wyłącznie niejednoznaczność provenance przy wielu równocześnie applicable `EMPLOYEE_DAY_ONLY_N_EXCEPTION` autoryzujących ten sam employee / N demand / date.

Nie zmienia:
- legalności fallbacku;
- persisted rule shape;
- kolejności retry;
- `exceptional_n_count`;
- lexicographic objective;
- żadnego HARD poza wcześniej zamrożonym wąskim DAY_ONLY fallback;
- zasady dokładnie jednego warningu na faktycznie użyte Assignment.

## CANONICAL AUTHORIZING RULE VERSION

Dla jednego employee oraz `ShiftDemand.start_datetime.date()` najpierw zbuduj zbiór wszystkich reguł, które jednocześnie:

1. są applicable na tę datę według istniejącego `SiteRuleApplicability` / T005 effective-selection semantics;
2. mają `rule_kind=EMPLOYEE_DAY_ONLY_N_EXCEPTION`;
3. mają `category=CONFIRMED_EXCEPTION`;
4. mają `enforcement=HARD`;
5. mają `resolution_status=RESOLVED`;
6. mają `structured_parameters.employee_id` równe employee.

Jeżeli zbiór jest pusty, DAY_ONLY N nie jest autoryzowana.

Jeżeli zbiór zawiera jedną lub więcej reguł, canonical `authorizing_rule_version_id` jest:

`min(rule.rule_version_id)`

czyli leksykograficznie najmniejszy exact string `rule_version_id`, w deterministycznym, locale-independent ordinal/string ordering.

Kolejność wejściowej listy `site_rules` / `applicable_hard_rules` nie może wpływać na wynik.

To jest wyłącznie techniczny tie-break provenance pomiędzy semantycznie równoważnymi autoryzacjami. Nie nadaje starszej/nowszej regule większej mocy, nie wybiera innego zachowania produktu i nie zmienia liczby exceptional N.

## ONE ASSIGNMENT = ONE USAGE = ONE WARNING

Jeżeli kilka równoważnych zgód autoryzuje ten sam wybrany N Assignment:
- Assignment liczy się dokładnie raz do `exceptional_n_count`;
- powstaje dokładnie jeden `DAY_ONLY-N-FALLBACK-01` warning;
- warning zawiera wyłącznie canonical `authorizing_rule_version_id` wybrany powyższą regułą;
- pozostałe równoważne IDs nie tworzą dodatkowych warningów ani dodatkowych kar.

## IDENTICAL OWNER ACROSS LIVE PATHS

Wąski pure helper w `rota/planning/site_rules.py` ma być jednym ownerem tego wyboru i może zwracać `rule_version_id | None` zamiast samego bool.

Ten sam helper/semantyka jest używany przez:
- fallback-enabled eligibility / solver slot provenance;
- independent validator warning/provenance;
- deterministic reconstruction z persisted schedule.

Nie implementować osobnych tie-breaków w solverze i validatorze.

## DURABLE RECONSTRUCTION

Po select/restart/finalize canonical ID musi być identyczny z ID użytym przy planowaniu.

Rekonstrukcja bierze pod uwagę wyłącznie autoryzacje należące do frozen provenance danego ScheduleVersion:
- `ScheduleVersion.applied_rule_version_ids` wyznacza dozwolony zbiór persisted rule versions;
- immutable SiteRuleVersion history + istniejące T005 effective-selection/applicability semantics wyznaczają, które z tych wersji są applicable na demand start date;
- reguły utworzone później i nieobecne w `applied_rule_version_ids` nie mogą zmienić historycznego warningu;
- na wynikowym applicable zbiorze stosuje się dokładnie ten sam `min(rule_version_id)`.

Nie dodawać nowej tabeli, pola Assignment, DecisionRecord ani warning row.

## REQUIRED ORACLES

1. Dwie różne rule families (`rule_id`) mają równocześnie applicable `EMPLOYEE_DAY_ONLY_N_EXCEPTION` dla tego samego employee/date: slot jest autoryzowany raz.
2. Input order A,B i B,A daje ten sam canonical ID = `min(rule_version_id)`.
3. Warning jest dokładnie jeden i zawiera canonical ID.
4. `exceptional_n_count` dla Assignment pozostaje 1, nie 2.
5. Po select + restart/finalize reconstruction zwraca ten sam canonical ID.
6. Późniejsza, nieobecna w `ScheduleVersion.applied_rule_version_ids` zgoda nie zmienia historycznego canonical ID.
