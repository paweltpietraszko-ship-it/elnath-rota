# TASK_CONTRACT

TASK_ID: ROTA-T005
TITLE: SiteMemory + Decision Ledger
STATUS: ARCHITECTURE_APPROVED_FOR_IMPLEMENTATION
DATE: 2026-08-12
BASE_DEPENDENCY: accepted ROTA-T004
ARCHITECT_ROLE: ChatGPT architect
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: ChatGPT architect
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: yes

## PURPOSE / WORKFLOW TRACE

Ten plik jest artefaktem architektonicznym pozostawionym celowo w repo, aby można było później odtworzyć workflow i provenance decyzji.

UWAGA PROVENANCE: wcześniejsza robocza propozycja architekta zakładająca wyłącznie prosty Rule Store bez wartościowej warstwy historii decyzji została odrzucona przed przekazaniem do implementacji. Niniejszy Task Contract ją zastępuje.

Podział ról:
- architekt projektuje Task Contract i rozstrzyga kwestie techniczne w granicach kanonu;
- CC implementuje wyłącznie zaakceptowany zakres;
- Codex audytuje implementację względem kontraktu i frozen spec;
- po audycie rezultat wraca do architekta do finalnego architectural PASS/FAIL;
- materialne decyzje produktowe pozostają po stronie właściciela.

## OWNER DECISION — 2026-08-12 — ZERO BIUROKRACJI

Koordynator wprowadza regułę w naturalnym języku, np.:

`Pracownik A pracuje tylko w weekendy.`

Dla koordynatora jest to pojedyncza czynność.

Nie wymagamy od niego:
- wyboru `rule_kind`;
- ręcznego wypełniania `structured_parameters`;
- formularza parametrów reguły;
- dodatkowego ekranu zatwierdzania;
- wieloetapowego workflow.

Program odpowiada za przekształcenie jednoznacznej wypowiedzi do struktury potrzebnej do wykonania reguły.

Jeżeli wypowiedź jest rzeczywiście niejednoznaczna, program zadaje jedno możliwie konkretne pytanie wyjaśniające.

`structured_parameters` jest szczegółem wewnętrznym programu i nie stanowi interfejsu pracy koordynatora.

Priorytet UX: Rota jest asystentem do budowania grafiku, nie systemem sprawozdawczo-kontrolnym. Nie dodawać ceremonii i zabezpieczeń niewymaganych przez kontrakt lub rzeczywistą niejednoznaczność.

## OBJECTIVE

Zbudować pamięć Site, która ma dwie odpowiedzialności:

A. Rule Store — przechowuje strukturalne `SiteRuleVersion` używane przez program.

B. Decision Ledger — przechowuje ludzką decyzję, z której dana zmiana wynikła, oraz pozwala później prześledzić jej historię.

Docelowy przepływ:

`decyzja człowieka -> zachowany oryginalny sens -> strukturalna reguła programu -> PlanningState`

Program ma móc odpowiedzieć zarówno:
- jaka reguła obowiązuje;
- dlaczego obowiązuje;
- kto ją zmienił;
- kiedy ją zmienił;
- co obowiązywało wcześniej;
- jaka późniejsza decyzja zastąpiła lub skorygowała wcześniejszą.

## ARCHITECTURE DECISION — SELECTIVE EME REUSE

T005 nie uruchamia pełnego Elnath Memory Engine jako osobnej usługi ani osobnej wspólnej bazy.

Z EME zachowujemy/adaptujemy wartościowe wzorce:
- append-only decision records;
- append-only relations;
- `supersedes`;
- `corrects`;
- `rejects`;
- wyprowadzanie aktualnego statusu z historii;
- możliwość prześledzenia decyzji wstecz.

Nie przenosimy do Rota:
- git/diff/patch review machinery;
- archive ingest;
- obowiązkowych `Span` dla zwykłej decyzji wpisanej bezpośrednio w Rota;
- obowiązkowego technicznego Evidence workflow dla takiej decyzji;
- ról EME `OWNER / IMPLEMENTER / GUARD` jako ról domenowych Rota;
- agentic retrieval/RRF/semantic search;
- osobnej usługi;
- wspólnej bazy;
- automatycznego back-sync.

Reuse ma być kopią/adaptacją wzorca zgodnie z frozen reuse map, nie runtime dependency na zewnętrzny EME.

## RULE STORE

`SiteRuleVersion` pozostaje strukturalnym źródłem dla programu.

Persistować istniejące pola domenowe:
- `rule_version_id`
- `rule_id`
- `site_id`
- `category`
- `rule_kind`
- `structured_parameters`
- `enforcement`
- `resolution_status`
- `effective_from`
- `effective_to`
- `changed_at`
- `changed_by`
- `supersedes_rule_version_id`
- `description`
- `source`
- `reason`

`SiteRuleVersion` jest append-only.

Po utworzeniu wersji:
- brak UPDATE;
- brak DELETE.

Zmiana zasady tworzy nową wersję.

Rozwiązanie wcześniej nierozpoznanej reguły również tworzy nową wersję zamiast modyfikować poprzedni rekord.

## RULE FAMILY INTEGRITY

Jedna rodzina `rule_id` należy zawsze do dokładnie jednego `site_id`.

`supersedes_rule_version_id`, jeżeli występuje:
- musi wskazywać istniejącą wersję;
- musi dotyczyć tego samego `rule_id`;
- musi dotyczyć tego samego `site_id`;
- nie może wskazywać samej siebie.

## structured_parameters

`structured_parameters` jest wewnętrzną reprezentacją programu i dla T005 ma być trwałym obiektem danych zgodnym z JSON z kluczami tekstowymi.

Persistence:
- zapisuje go jako JSON;
- odczytuje bez zmiany znaczenia;
- nie interpretuje parametrów;
- nie zna katalogu `rule_kind`.

T005 nie projektuje katalogu `rule_kind` i nie implementuje interpretera naturalnego języka.

Dla `NEEDS_RESOLUTION` `rule_kind` i/lub `structured_parameters` mogą pozostać puste zgodnie z frozen contract.

Wolny tekst sam nie staje się logiką solvera.

## DECISION LEDGER

Każda decyzja dotycząca `SiteRule` ma immutable rekord zawierający co najmniej:
- `decision_id`
- `site_id`
- `rule_id`
- `statement` — oryginalna wypowiedź koordynatora zachowana bez przepisywania jej przez model
- `coordinator_id`
- `recorded_at` — kiedy decyzja została rzeczywiście podjęta/zapisana
- `rule_version_id` — dokładna strukturalna wersja reguły utworzona przez tę decyzję

Jeżeli czas podjęcia decyzji różni się od czasu jej obowiązywania, źródłem okresu obowiązywania pozostaje `SiteRuleVersion.effective_from/effective_to`.

`powiedział to 16 maja` i `reguła zaczęła obowiązywać 1 czerwca` to dwa różne fakty i nie wolno ich zlewać.

## DECISION IMMUTABILITY

Decision Record po utworzeniu:
- nie podlega UPDATE;
- nie podlega DELETE.

Jeżeli koordynator zmieni zdanie, powstaje nowy Decision Record i nowa `SiteRuleVersion`.

Stary wpis pozostaje dostępny historycznie.

## DECISION RELATIONS / FATE

Minimalne relacje historii decyzji:

`supersedes` — nowa decyzja zastępuje wcześniejszą.

`corrects` — nowa decyzja koryguje błędnie zapisaną wcześniejszą decyzję.

`rejects` — wcześniejsza decyzja zostaje świadomie odrzucona.

Relacje są append-only.

Status decyzji jest wyprowadzany z historii, nie ręcznie nadpisywany.

Minimalne statusy potrzebne Rota:
- `ACTIVE`
- `SUPERSEDED`
- `REJECTED`

Informację o korekcie zachowuje relacja `corrects`; wcześniejszy rekord nie znika.

Nie budować rozbudowanego workflow statusów EME.

## ATOMICITY

Jedna czynność koordynatora nie może zakończyć się sytuacją, w której Decision Ledger mówi jedno, a Rule Store drugie.

Utworzenie zmiany reguły jest jedną transakcją obejmującą:
- Decision Record;
- `SiteRuleVersion`;
- ewentualną relację do poprzedniej decyzji.

Albo wszystkie elementy powstają, albo żaden.

To zabezpieczenie jest niewidoczne dla użytkownika.

## RETRIEVAL / HISTORY API

SiteMemory ma umożliwiać co najmniej:

### 1. Historia reguły

Dla `rule_id` zwrócić wszystkie decyzje chronologicznie wraz z ich relacjami i odpowiadającymi `rule_version_id`.

### 2. Co obowiązywało danego dnia

Dla `rule_id + date` ustalić dokładną wersję reguły i odpowiadającą decyzję obowiązującą wtedy.

### 3. Dlaczego obowiązuje obecna reguła

Dla `rule_version_id` odnaleźć decyzję, która ją utworzyła, oraz wcześniejszy łańcuch decyzji.

Przyszłe UI ma dzięki temu móc pokazać np.:

`Ta zasada obowiązuje od 16 maja. Wprowadził ją koordynator X. Zastąpiła decyzję z 10 marca.`

Bez czytania technicznych logów.

## EFFECTIVE HISTORY

Retrieval dla reguł uwzględnia:
- `effective_from`;
- `effective_to`;
- supersession;
- okres zapytania.

Zmiana w połowie miesiąca nie może powodować zastosowania nowej wersji do wcześniejszych dni.

Nie wolno redukować historii do zasady `po prostu najnowsza wersja`.

## PROJECTION TO PLANNINGSTATE

PlanningEngine nie czyta Decision Ledger ani bazy.

Warstwa assembly pobiera reguły i dzieli je:

`RESOLVED` -> `PlanningState.site_rules`

`NEEDS_RESOLUTION` -> `PlanningState.unresolved_site_rules`

`NEEDS_RESOLUTION` nigdy nie trafia do executable rule set.

`INFORMATIONAL` nie może tworzyć constraintu PlanningEngine.

T005 nie implementuje wykonywania `rule_kind` przez solver.

## SOURCE / PROVENANCE FOR COORDINATOR DECISION

Dla decyzji wpisanej bezpośrednio w Rota provenance jest proste i automatyczne:
- kto: `coordinator_id`;
- kiedy: `recorded_at`;
- co powiedział: niezmieniony `statement`;
- co z tego powstało: `rule_version_id`.

Nie wymaga to od człowieka żadnej dodatkowej pracy.

Jeśli w przyszłości reguła pochodzi z dokumentu klienta lub innego źródła, istniejące `SiteRuleVersion.source` może zachować takie źródło. T005 nie rozbudowuje tego teraz.

## DECISION_REQUIRED

Nie mapować `DecisionRequiredPayload` na EME `DEC`, `Record` ani SiteRule w T005.

To pozostaje poza zakresem tego zadania.

## TASK_SCOPE

Dozwolone:
- schema SiteRule/SiteRuleVersion w lokalnej bazie Rota utworzonej przez T004;
- Decision Ledger tables/model;
- append-only relations `supersedes/corrects/rejects`;
- SiteRule persistence;
- SiteMemory retrieval/history API;
- minimalna korekta reprezentacji `RuleParameters` zgodnie z tym Task Contract;
- testy T005;
- minimalny assembly helper/API do rozdzielenia resolved/unresolved, bez PlanningEngine I/O.

## OUT_OF_SCOPE

Nie implementować:
- katalogu `rule_kind`;
- solver execution dla SiteRule;
- natural-language parsera;
- LLM;
- szczegółowego UI historii;
- formularzy technicznych;
- approval workflow;
- desktop bridge;
- pełnego EME runtime;
- semantic search/RRF;
- archive ingest;
- git/review machinery EME;
- DecisionRequired->memory mapping;
- zmian PlanningEngine;
- zmian `arch/spec.md`.

## ACCEPTANCE CONTRACT

PASS wymaga łącznie:
1. Decision Record i odpowiadająca `SiteRuleVersion` powstają atomowo.
2. Stara decyzja nigdy nie jest nadpisywana ani usuwana.
3. Stara `SiteRuleVersion` pozostaje niezmieniona.
4. Zmiana decyzji tworzy nową decyzję i nową wersję reguły.
5. Można odtworzyć chronologiczną historię jednej reguły.
6. Można wskazać, która decyzja zastąpiła, skorygowała lub odrzuciła którą.
7. Można ustalić, co obowiązywało konkretnego dnia.
8. Można przejść od `rule_version_id` do ludzkiej decyzji, która je spowodowała.
9. Zachowany jest dokładny tekst wpisany przez koordynatora.
10. Zachowany jest koordynator i czas decyzji.
11. `structured_parameters` przechodzi poprawny JSON round-trip i persistence nie interpretuje jego semantyki.
12. `NEEDS_RESOLUTION` nie pojawia się w executable rule set.
13. `NEEDS_RESOLUTION` pozostaje dostępne do wyświetlenia/rozstrzygnięcia.
14. PlanningEngine nie wykonuje I/O i nie czyta Decision Ledger.
15. Wolny tekst sam nie jest wykonywany przez solver.
16. Nie istnieje obowiązek Evidence/Span dla zwykłej decyzji koordynatora.
17. Nie powstaje dodatkowy krok UX tylko po to, aby zapisać historię.
18. Nie ma zależności od działającej usługi EME ani wspólnej bazy.
19. Nie ma git/review/archive machinery EME.
20. Stare decyzje pozostają dostępne również wtedy, gdy dawno przestały obowiązywać.
21. Retrieval uwzględnia `effective_from`, `effective_to` i supersession; zmiana w środku miesiąca nie działa wstecz.
22. T005 nie zmienia `arch/spec.md`.

## ARCHITECTURAL INTENT

Pamięć ma zmniejszać ciężar pamiętania po stronie człowieka, nie zwiększać ciężar obsługi programu.

Koordynator zmienia zasadę raz.

Program pamięta resztę.

Wartość funkcjonalna Decision Ledger obejmuje sytuacje sporów/rozjazdów: program ma umożliwiać pokazanie historycznego faktu typu `16 maja koordynator zmienił tę decyzję`, wraz z poprzednikiem i późniejszym losem decyzji.

## PROCESS

T005 startuje dopiero od SHA po zaakceptowanym T004.

CC implementuje dokładnie powyższy zakres.

Gdy CC natrafi na decyzję zmieniającą zachowanie produktu, zgłasza `CONTRACT_GAP` zamiast rozstrzygać ją samodzielnie.

Codex audytuje implementację, ale nie zmienia architektury ani produktu.

Po audycie rezultat wraca do architekta do finalnego architectural PASS/FAIL.
