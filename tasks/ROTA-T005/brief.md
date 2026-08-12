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

UWAGA PROVENANCE:
- wcześniejsza robocza propozycja architekta zakładająca wyłącznie prosty Rule Store bez wartościowej warstwy historii decyzji została odrzucona przed przekazaniem do implementacji;
- pierwsza wersja niniejszego T005 została następnie poddana przeglądowi przed implementacją; przegląd wskazał brak semantyki spójności obu historii, jednoznacznego wyboru wersji dla daty oraz `rejects/corrects`;
- niniejsza rewizja zamyka te luki przed rozpoczęciem implementacji T005.

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

## OWNER DECISION — 2026-08-12 — `effective_to` JEST INCLUSIVE

Znaczenie dla człowieka jest literalne:

`obowiązuje do 31 maja` oznacza, że reguła obowiązuje przez cały 31 maja i wygasa dopiero z końcem tego dnia.

W domenie datowej T005:
- `effective_from` jest pierwszym dniem obowiązywania — inclusive;
- `effective_to`, gdy istnieje, jest ostatnim dniem obowiązywania — inclusive.

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
- jaka późniejsza decyzja zastąpiła, skorygowała albo odrzuciła wcześniejszą.

## ARCHITECTURE DECISION — SELECTIVE EME REUSE

T005 nie uruchamia pełnego Elnath Memory Engine jako osobnej usługi ani osobnej wspólnej bazy.

Z EME zachowujemy/adaptujemy wartościowe wzorce:
- append-only decision records;
- append-only relations;
- `supersedes`;
- `corrects`;
- `rejects`;
- wyprowadzanie losu decyzji z historii;
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

Zmiana strukturalnej treści reguły tworzy nową wersję.

Rozwiązanie wcześniej nierozpoznanej reguły również tworzy nową wersję zamiast modyfikować poprzedni rekord.

## RULE FAMILY INTEGRITY

Jedna rodzina `rule_id` należy zawsze do dokładnie jednego `site_id`.

`supersedes_rule_version_id`, jeżeli występuje:
- musi wskazywać istniejącą wersję;
- musi dotyczyć tego samego `rule_id`;
- musi dotyczyć tego samego `site_id`;
- nie może wskazywać samej siebie.

## `structured_parameters` — WYŁĄCZNIE FORMAT PERSISTENCE

JSON w T005 jest wyłącznie formatem trwałego zapisu danych `structured_parameters`.

Nie jest to decyzja, że domenowym typem `RuleParameters` ma być `dict`.
Nie jest to decyzja przeciw przyszłemu typed union per `rule_kind`.
Nie rozstrzyga to katalogu `rule_kind`.

`RuleParameters` pozostaje CONTRACT_GAP dla osobnego zadania.

Persistence boundary:
- serializuje aktualną wartość `structured_parameters` do reprezentacji JSON-compatible;
- odczytuje ją bez zmiany znaczenia;
- nie interpretuje parametrów;
- nie zna katalogu `rule_kind`;
- nie ustanawia docelowego typu domenowego.

Do czasu zdefiniowania typed `RuleParameters` testy persistence mogą używać JSON-compatible obiektów jako fixtures, ale nie wolno na tej podstawie zamrozić typu domenowego ani zmienić kanonu.

Dla `NEEDS_RESOLUTION` `rule_kind` i/lub `structured_parameters` mogą pozostać puste zgodnie z frozen contract.

Wolny tekst sam nie staje się logiką solvera.

## DECISION LEDGER

Każda decyzja zmieniająca stan rodziny `SiteRule` ma immutable Decision Record zawierający co najmniej:
- `decision_id`
- `site_id`
- `rule_id`
- `statement` — oryginalna wypowiedź koordynatora zachowana bez przepisywania jej przez model
- `coordinator_id`
- `recorded_at` — kiedy decyzja została rzeczywiście podjęta/zapisana
- `effective_from` — pierwszy dzień, od którego ta decyzja ma wpływ na stan reguły; inclusive
- `rule_version_id` — OPTIONAL; dokładna strukturalna wersja reguły utworzona przez tę decyzję, jeżeli decyzja tworzy aktywną treść reguły

Jeżeli Decision Record ma `rule_version_id`, musi zachodzić pełna spójność:
- DecisionRecord.site_id == SiteRuleVersion.site_id;
- DecisionRecord.rule_id == SiteRuleVersion.rule_id;
- DecisionRecord.coordinator_id == SiteRuleVersion.changed_by;
- DecisionRecord.recorded_at == SiteRuleVersion.changed_at;
- DecisionRecord.effective_from == SiteRuleVersion.effective_from.

Jeżeli czas podjęcia decyzji różni się od czasu jej obowiązywania, są to dwa różne fakty:

`powiedział to 16 maja` != `reguła zaczęła obowiązywać 1 czerwca`.

## DECISION IMMUTABILITY

Decision Record po utworzeniu:
- nie podlega UPDATE;
- nie podlega DELETE.

Jeżeli koordynator zmieni zdanie, powstaje nowy Decision Record.

Jeżeli ta nowa decyzja ustanawia nową strukturalną treść reguły, powstaje również nowa `SiteRuleVersion`.

Jeżeli decyzja wyłącznie odrzuca obowiązującą regułę (`rejects`), nie powstaje fikcyjna `SiteRuleVersion` tylko po to, aby reprezentować "brak reguły".

Stare wpisy pozostają dostępne historycznie.

## LINEAR DECISION CHAIN — ZERO BRANCHING

Dla jednego `(site_id, rule_id)` Decision Ledger tworzy jeden liniowy łańcuch zmian stanu.

Pierwsza decyzja rodziny nie ma poprzednika.

Każda kolejna decyzja zmieniająca stan:
- ma dokładnie jedną relację stanu do aktualnego końca łańcucha;
- relacja ma typ dokładnie jeden z: `supersedes`, `corrects`, `rejects`;
- nie może wskazywać dowolnej starszej decyzji z pominięciem aktualnego końca;
- nie może tworzyć drugiego następcy dla tego samego końca;
- nie może tworzyć cyklu.

W efekcie dla jednej rodziny nie istnieją dwie konkurencyjne gałęzie historii.

Kolejność w łańcuchu oznacza kolejność późniejszych decyzji/provenance. Nie należy jej mylić z `recorded_at` ani z chronologicznym porządkiem `effective_from`.

To celowe: można wcześniej zapisać decyzję, która ma wejść w życie w przyszłości, a potem przed jej wejściem podjąć następną decyzję, która ją zastępuje lub koryguje.

## DECISION RELATIONS / FATE

### `supersedes`

Nowa decyzja zastępuje aktualny koniec łańcucha od swojego `effective_from`.

Jeżeli zarówno nowa decyzja, jak i decyzja zastępowana mają `rule_version_id`, to:

`new_site_rule_version.supersedes_rule_version_id == previous_decision.rule_version_id`

To jest obowiązkowy invariant spójności Rule Store <-> Decision Ledger.

Jeżeli poprzedni koniec łańcucha jest `rejects` i nie ma `rule_version_id`, nowa aktywna reguła może go zastąpić, ale jej `SiteRuleVersion.supersedes_rule_version_id` musi być `None`, ponieważ nie istnieje bezpośrednio zastępowana aktywna `SiteRuleVersion`.

### `corrects`

`corrects` oznacza: nowa decyzja koryguje treść/interpretację aktualnego końca łańcucha i ustanawia nową strukturalną wersję reguły.

Wymagania:
- decyzja korygująca ma `rule_version_id`;
- decyzja korygowana ma `rule_version_id`;
- `new_site_rule_version.supersedes_rule_version_id == corrected_decision.rule_version_id`;
- wpływ korekty zaczyna się dokładnie od `new_decision.effective_from`;
- korekta nie jest automatycznie retroaktywna do daty wcześniejszej decyzji; retroaktywność istnieje tylko wtedy, gdy jawnie podane `effective_from` nowej decyzji wskazuje taką wcześniejszą datę.

Relacja `corrects` zachowuje provenance, dlaczego powstała nowa wersja; dla wyboru obowiązującej wersji jest zmianą stanu tak samo jak `supersedes`.

### `rejects`

`rejects` oznacza: od `new_decision.effective_from` rodzina reguły nie ma aktywnej reguły, dopóki późniejsza decyzja nie ustanowi kolejnej.

Wymagania:
- nowy Decision Record ma `rule_version_id = None`;
- odrzucana decyzja musi być aktualnym końcem łańcucha i mieć `rule_version_id`;
- nie tworzyć fikcyjnego `SiteRuleVersion` ze stanem "disabled";
- nie modyfikować starego `SiteRuleVersion.effective_to`.

Późniejsze przywrócenie reguły jest nową decyzją z nową `SiteRuleVersion`; może `supersede` Decision Record odrzucenia. Ponieważ odrzucenie nie ma `rule_version_id`, nowa wersja po przerwie ma `supersedes_rule_version_id = None`.

## LOS DECYZJI A OBOWIĄZYWANIE NA DATĘ

Minimalne historyczne statusy/fates Decision Record:
- `ACTIVE`
- `SUPERSEDED`
- `REJECTED`

Informację o korekcie zachowuje relacja `corrects`; wcześniejszy rekord nie znika.

WAŻNE: historyczny fate nie jest samodzielnym algorytmem wyboru reguły dla daty.

Przykład: jeżeli decyzja B została już zapisana i `supersedes` A, ale B.effective_from jest 1 czerwca, to 20 maja A nadal może być regułą obowiązującą. Retrieval zawsze używa reguł z sekcji EFFECTIVE SELECTION poniżej.

## ATOMICITY

Jedna czynność koordynatora nie może zakończyć się sytuacją, w której Decision Ledger mówi jedno, a Rule Store drugie.

Jedna transakcja obejmuje odpowiednio:
- nowy Decision Record;
- nową `SiteRuleVersion`, jeśli decyzja tworzy nową treść reguły;
- relację do poprzedniego końca łańcucha, jeśli to nie jest pierwsza decyzja.

Dodatkowo w tej samej transakcji muszą zostać sprawdzone invarianty spójności obu historii opisane w tym kontrakcie.

Albo całość powstaje poprawnie, albo nie powstaje żaden fragment zmiany.

To zabezpieczenie jest niewidoczne dla użytkownika.

## EFFECTIVE SELECTION — JEDNOZNACZNY ALGORYTM

Dla jednego `(site_id, rule_id)` oraz daty `D` obowiązuje dokładnie następujący algorytm.

1. Pobierz liniowy łańcuch Decision Record od najstarszego do aktualnego końca.
2. Odrzuć z rozważania decyzje, dla których `effective_from > D`.
3. Z pozostałych wybierz decyzję najpóźniejszą W ŁAŃCUCHU, nie tę z najpóźniejszym `recorded_at` i nie tę z największym `effective_from`.
4. Jeżeli nie ma takiej decyzji -> dla tej rodziny `NO_ACTIVE_RULE` w dniu D.
5. Jeżeli wybrana decyzja jest `rejects` (`rule_version_id = None`) -> `NO_ACTIVE_RULE` w dniu D.
6. Jeżeli wybrana decyzja ma `rule_version_id`, pobierz dokładnie tę `SiteRuleVersion`.
7. Jeżeli jej `effective_to is not None` oraz `D > effective_to` -> `NO_ACTIVE_RULE` w dniu D. Nie wolno "wskrzeszać" starszej wersji po wygaśnięciu nowszej.
8. W przeciwnym razie dokładnie ta `SiteRuleVersion` jest wersją obowiązującą w dniu D.

Konsekwencje:
- zapis przyszłej decyzji wcześniej nie zmienia stanu przed jej `effective_from`;
- późniejsza decyzja może zastąpić/korygować wcześniej zapisaną przyszłą decyzję jeszcze przed jej wejściem w życie;
- nie ma konfliktu dwóch gałęzi, bo gałęzie są zabronione;
- `effective_to=None` nie wymaga późniejszej modyfikacji: późniejsza decyzja przejmuje stan od własnego `effective_from`;
- wersja z jawnym `effective_to` wygasa z końcem tej daty; po niej nie wraca automatycznie wcześniejsza reguła;
- zmiana w połowie miesiąca nie działa wstecz.

### Przykład przyszłej decyzji

A:
- zapis 1 marca;
- effective_from = 1 marca.

B supersedes A:
- zapis 10 marca;
- effective_from = 1 czerwca.

Dla 20 maja -> A.
Dla 10 czerwca -> B.

Jeżeli 15 kwietnia powstanie C, które supersedes B i ma effective_from = 1 maja:
- dla 20 kwietnia -> A;
- dla 20 maja -> C;
- dla 10 czerwca -> C.

B pozostaje w historii, ale nigdy nie staje się obowiązującą wersją, ponieważ późniejsza w łańcuchu decyzja C przejęła stan wcześniej.

## RETRIEVAL / HISTORY API

SiteMemory ma umożliwiać co najmniej:

### 1. Historia reguły

Dla `rule_id` zwrócić wszystkie decyzje w kolejności łańcucha wraz z:
- `recorded_at`;
- `effective_from`;
- relacją do poprzednika;
- odpowiadającym `rule_version_id`, jeśli istnieje.

### 2. Co obowiązywało danego dnia

Dla `rule_id + date` zastosować dokładnie EFFECTIVE SELECTION powyżej i zwrócić:
- jedną `SiteRuleVersion` + Decision Record;
- albo jawny wynik `NO_ACTIVE_RULE`.

Nigdy nie wybierać arbitralnie jednej z wielu wersji przez `ORDER BY changed_at DESC LIMIT 1`, `MAX(effective_from)` ani podobny skrót.

### 3. Dlaczego obowiązuje obecna reguła

Dla `rule_version_id` odnaleźć Decision Record, który ją utworzył, oraz wcześniejszy łańcuch decyzji.

Przyszłe UI ma dzięki temu móc pokazać np.:

`Ta zasada obowiązuje od 16 maja. Wprowadził ją koordynator X. Zastąpiła decyzję z 10 marca.`

Bez czytania technicznych logów.

## PROJECTION TO PLANNINGSTATE

PlanningEngine nie czyta Decision Ledger ani bazy.

Warstwa assembly pobiera reguły dla dni/okresu planowania zgodnie z EFFECTIVE SELECTION.

`RESOLVED` -> `PlanningState.site_rules`

`NEEDS_RESOLUTION` -> `PlanningState.unresolved_site_rules`

`NEEDS_RESOLUTION` nigdy nie trafia do executable rule set.

`INFORMATIONAL` nie może tworzyć constraintu PlanningEngine.

T005 nie implementuje wykonywania `rule_kind` przez solver.

## SOURCE / PROVENANCE FOR COORDINATOR DECISION

Dla decyzji wpisanej bezpośrednio w Rota provenance jest proste i automatyczne:
- kto: `coordinator_id`;
- kiedy podjął/zapisał: `recorded_at`;
- od kiedy ma wpływ: `effective_from`;
- co powiedział: niezmieniony `statement`;
- co z tego powstało: `rule_version_id`, jeśli powstała strukturalna wersja.

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
- integralność liniowego łańcucha;
- integralność Rule Store <-> Decision Ledger;
- SiteRule persistence;
- SiteMemory retrieval/history API;
- JSON persistence adapter dla `structured_parameters` bez rozstrzygania domenowego `RuleParameters`;
- neutralizacja niezweryfikowanego komentarza w `rota/domain.py` sugerującego, że typed union został zamrożony, przy zachowaniu `RuleParameters` jako CONTRACT_GAP;
- testy T005;
- minimalny assembly helper/API do rozdzielenia resolved/unresolved, bez PlanningEngine I/O.

## OUT_OF_SCOPE

Nie implementować:
- katalogu `rule_kind`;
- domenowego typed union `RuleParameters`;
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
1. Decision Record i odpowiadająca `SiteRuleVersion`, jeśli występuje, powstają atomowo z relacją stanu.
2. Stara decyzja nigdy nie jest nadpisywana ani usuwana.
3. Stara `SiteRuleVersion` pozostaje niezmieniona; późniejsza decyzja nie wymaga UPDATE starego `effective_to`.
4. Dla jednego `(site_id, rule_id)` istnieje dokładnie jeden liniowy łańcuch bez branchy i cykli.
5. Każda kolejna decyzja stanu wskazuje aktualny koniec łańcucha, nie dowolnego starszego przodka.
6. Dla `supersedes/corrects` dwóch decyzji mających `rule_version_id`, nowa `SiteRuleVersion.supersedes_rule_version_id` wskazuje dokładnie `rule_version_id` decyzji będącej celem relacji.
7. Decision Record i `SiteRuleVersion` mają zgodne `site_id`, `rule_id`, autora, czas zapisu i `effective_from`.
8. `rejects` nie tworzy fikcyjnej `SiteRuleVersion`; od swojego `effective_from` daje `NO_ACTIVE_RULE` do czasu kolejnej decyzji ustanawiającej regułę.
9. `corrects` tworzy nową wersję i działa od jawnego `effective_from`; nie ma ukrytej retroaktywności.
10. Można odtworzyć pełną historię jednej reguły wraz z decyzjami, datami i relacjami.
11. Można wskazać, która decyzja zastąpiła, skorygowała lub odrzuciła którą.
12. Dla `rule_id + date` EFFECTIVE SELECTION zwraca dokładnie jedną wersję albo `NO_ACTIVE_RULE`.
13. Przyszła decyzja zapisana wcześniej nie działa przed `effective_from`.
14. Późniejsza decyzja w łańcuchu może sprawić, że wcześniej zapisana przyszła wersja nigdy nie stanie się aktywna, bez usuwania jej z historii.
15. `effective_to` jest inclusive: wersja obowiązuje przez cały dzień `effective_to`.
16. Po wygaśnięciu nowszej wersji przez jej jawne `effective_to` starsza wersja nie odżywa automatycznie.
17. Można przejść od `rule_version_id` do ludzkiej decyzji, która je spowodowała.
18. Zachowany jest dokładny tekst wpisany przez koordynatora.
19. Zachowany jest koordynator, `recorded_at` i `effective_from` decyzji.
20. JSON jest wyłącznie formatem persistence dla `structured_parameters`; T005 nie zamraża domenowego `dict`, typed union ani katalogu `rule_kind`.
21. `NEEDS_RESOLUTION` nie pojawia się w executable rule set.
22. `NEEDS_RESOLUTION` pozostaje dostępne do wyświetlenia/rozstrzygnięcia.
23. PlanningEngine nie wykonuje I/O i nie czyta Decision Ledger.
24. Wolny tekst sam nie jest wykonywany przez solver.
25. Nie istnieje obowiązek Evidence/Span dla zwykłej decyzji koordynatora.
26. Nie powstaje dodatkowy krok UX tylko po to, aby zapisać historię.
27. Nie ma zależności od działającej usługi EME ani wspólnej bazy.
28. Nie ma git/review/archive machinery EME.
29. Stare decyzje pozostają dostępne również wtedy, gdy nigdy nie weszły w życie albo dawno przestały obowiązywać.
30. T005 nie zmienia `arch/spec.md`.

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
