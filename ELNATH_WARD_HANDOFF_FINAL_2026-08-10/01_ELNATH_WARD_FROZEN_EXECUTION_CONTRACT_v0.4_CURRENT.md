# ELNATH WARD — FROZEN EXECUTION CONTRACT v0.4
Status: CANDIDATE DO ZAMROŻENIA
Data: 2026-08-10
Zakres: Elnath Rota — proces implementacyjny, kanon produktu, reuse i granice autonomii modeli

## 1. Cel dokumentu

Ten dokument jest pojedynczym kontraktem wykonawczym dla Elnath Ward.

Jego celem jest wyeliminowanie sytuacji, w której implementer musi samodzielnie czytać kilka dokumentów, syntetyzować ich znaczenie i uzupełniać luki własnymi decyzjami.

Ward ma dostarczać implementerowi skompilowany Task Contract. Implementer nie rekonstruuje kanonu z rozmów, Spec, Architecture, checkpointów ani repozytoriów.

Zasada nadrzędna:

BRAK ODPOWIEDZI W KONTRAKCIE NIE JEST POZWOLENIEM NA DECYZJĘ IMPLEMENTERA.

Jeżeli materialne zachowanie nie wynika jednoznacznie z kontraktu, wynik brzmi CONTRACT_GAP i zadanie wraca przed implementację.

## 2. Kanoniczny pipeline Ward

1. Właściciel / Canon
   - ustala zachowanie produktu;
   - zatwierdza lub odrzuca decyzje produktowe;
   - nie jest implementerem.

2. Sonet — Task Slicer
   - otrzymuje zamrożony kontrakt produktu;
   - dzieli pracę na małe, możliwie lokalne Task Contracts;
   - nie zmienia zachowania produktu;
   - nie dodaje wymagań „dla bezpieczeństwa”, „na przyszłość” ani „przy okazji”;
   - jeżeli task wymaga niezamrożonej decyzji: CONTRACT_GAP.

3. Backend Ward — Mechanical Gate
   - mechanicznie sprawdza kompletność Task Contract;
   - sprawdza wersję kontraktu, scope, dozwolone pliki/moduły, wymagane wejścia i wyjścia, zakazy oraz acceptance checks;
   - blokuje task, jeżeli implementer musiałby zgadywać;
   - nie podejmuje decyzji produktowych.

4. Claude Code — Implementer
   - implementuje dokładnie Task Contract;
   - używa wskazanych komponentów REUSE/ADAPT;
   - nie zmienia polityki produktu;
   - nie pisze alternatywnej architektury;
   - nie rozszerza scope na podstawie własnej oceny;
   - nie może zamieniać CONTRACT_GAP na własną implementację.

5. Codex — Independent Tester / Auditor
   - testuje dokładny SHA;
   - sprawdza zachowanie, przypadki negatywne i kontraktowe;
   - PASS techniczny oznacza wyłącznie zgodność badanego SHA z testowanym kontraktem;
   - PASS nie oznacza zgody właściciela na zmianę produktu.

6. Sonet — Technical Acceptance
   - po raporcie Codexa sprawdza, czy task został wykonany zgodnie z lokalnym kontraktem;
   - nie rozszerza zakresu;
   - nie interpretuje PASS jako zgody na nowe zachowanie;
   - może zaakceptować task technicznie albo zwrócić go do poprawy.

7. Canon Guard — ChatGPT
   - sprawdza, czy cały ciąg nie odpłynął od kanonu produktu;
   - porównuje lokalnie poprawne zmiany z zamrożonym kontraktem produktu;
   - szuka zmian semantycznych, które mogły przejść lokalne testy;
   - nie zastępuje Codexa w testowaniu implementacji;
   - nie implementuje kodu;
   - wydaje końcową rekomendację zgodności z kanonem.

8. Właściciel
   - podejmuje ostateczną decyzję o przyjęciu materialnej zmiany produktu lub zmianie kontraktu.

## 3. Trzy poziomy prawdy

### 3.1 Source Documents
Pełne materiały projektowe i dowodowe:
- Spec Produktowa Rota;
- Architecture Rota;
- Checkpoint;
- decyzje właściciela;
- dokumentacja używanych repozytoriów;
- audyty.

Służą do utrzymania kanonu. Nie są domyślnym pakietem dla CC.

### 3.2 Frozen Product Contract
Jednoznaczny, wersjonowany kontrakt zachowania produktu:
- domena;
- HARD;
- SOFT;
- DECISION_REQUIRED;
- statusy wyników;
- granice autonomii;
- reuse map;
- zakazy.

To jest główna prawda Ward.

### 3.3 Task Contract
Minimalny wycinek Frozen Product Contract potrzebny do jednego zadania.

Musi zawierać:
- cel;
- wejścia;
- wyjścia;
- dotykane moduły;
- reguły obowiązujące w tym tasku;
- REUSE / ADAPT / NEW / FORBIDDEN;
- acceptance checks;
- zakazy;
- jawne CONTRACT_GAP conditions.

CC nie powinien potrzebować samodzielnie uzgadniać kilku dokumentów źródłowych.

## 4. Zasada kompilacji tasku

Ward nie przekazuje do CC szerokiej instrukcji typu:
„Przeczytaj Spec, Architecture, Memory Engine i Continuity UI, a następnie zbuduj funkcję.”

Ward przekazuje instrukcję typu:
- implementuj konkretny kontrakt;
- użyj wskazanego komponentu;
- nie dotykaj wskazanych warstw;
- zwróć dokładnie określony typ wyniku;
- nie wprowadzaj nowej polityki;
- jeśli wymagana polityka nie jest określona: CONTRACT_GAP.

Task jest niegotowy, jeżeli do jego wykonania potrzebna jest materialna decyzja implementera.

## 5. Rota — reuse map

### 5.1 REUSE / ADAPT: Continuity AI desktop shell
Źródło:
- repo: paweltpietraszko-ship-it/continuity-ai
- branch: ui/project-report-polish-v0.4
- punkt kontrolny używany jako baza: 709cf6a1ff829725e5d6572d286963809c990c4a

Do wykorzystania jako baza techniczna:
- Tauri 2;
- React 18;
- TypeScript;
- Vite;
- istniejący układ frontend/bridge/types/components;
- wzorzec lokalnego procesu Bridge;
- UTF-8 NDJSON;
- kontrolowane błędy;
- testowy toolchain frontendu i Rust.

Nie przenosić domeny Continuity AI:
- Project Report;
- Aurora;
- evidence map;
- conversation;
- attestations;
- logiki filmu/projektów;
- żadnych syntetycznych założeń domenowych.

UI Continuity jest dawcą shellu i wzorców technicznych, nie kontraktu produktu Rota.

### 5.2 REUSE SELECTIVE: Elnath Memory Engine
Źródło:
- repo: paweltpietraszko-ship-it/elnath-memory-engine
- branch: main
- provenance source commit: 3bdcd7909373ce541be5e6bd1a5a88b99623801b

Do rozważonego reuse:
- elnath/memory/ jako domenowo neutralna baza pamięci;
- append-only/history/source/retrieval patterns, jeśli odpowiadają kontraktowi Rota.

Warunek:
- Rota bierze własny fork/kopię;
- brak wspólnej usługi;
- brak wspólnej bazy;
- brak automatycznego back-sync.

NIE używać teraz:
- elnath/guard/review jako runtime Rota;
- code-review-specific diff/patch binding;
- mechanizmów git jako części domeny planowania.

### 5.3 BUILD NEW: Rota domain
Nowe i kanoniczne dla Rota:
- Site / SiteProfile;
- Employee / SiteMembership;
- Availability;
- ShiftDemand;
- Assignment;
- ScheduleVersion;
- WorkBalance;
- CalendarDay;
- ExternalSupportWindow;
- SiteRule adapter do PlanningState;
- PlanningState;
- PlanningEngine;
- REPLAN;
- mapowanie wyników do kontraktu UI.

Te elementy wynikają z Rota Product Contract, nie z Continuity ani starego Elnath Code.

### 5.4 REUSE: OR-Tools CP-SAT
Technologia solvera:
- Google OR-Tools CP-SAT.

Zakaz:
- CC nie implementuje własnego algorytmu scheduling/search/backtracking.

CC implementuje:
1. mapowanie domeny Rota -> model CP-SAT;
2. mapowanie HARD/SOFT/DECISION gates -> constraints/objective;
3. mapowanie wyniku CP-SAT -> Rota PlanningResult.

OR-Tools wykonuje wyszukiwanie kombinatoryczne.
Rota definiuje politykę produktu.

### 5.5 VERIFIED REFERENCE: minimalny PoC solvera

Decyzja o użyciu OR-Tools CP-SAT została zweryfikowana rzeczywistym uruchomieniem minimalnego proof-of-concept na Windows.

Scenariusz referencyjny:
- październik 2026;
- pracownicy A–E;
- dokładnie jedna D i jedna N każdego dnia;
- DAY_ONLY;
- DAY_SHIFT_OFF v0.3;
- LEAVE_GRANTED;
- UNAVAILABLE_24H liczone po rzeczywistych przedziałach czasu;
- REST-01 minimum 11 h;
- LOAD-01 każde ruchome 7 dni <= 60 h;
- X/Y wyłączone;
- mentor A PRIMARY D 8 października;
- target_hours jako SOFT objective.

Rzeczywisty wynik uruchomienia:
- CP-SAT status: OPTIMAL;
- niezależny validator: HARD PASS;
- minimum rest znalezione w wyniku: 12 h;
- maksimum w ruchomym oknie 7 dni: 60 h;
- godziny miesięczne:
  - A: 156 h;
  - B: 144 h;
  - C: 156 h;
  - D: 144 h;
  - E: 144 h;
- jedyne zgłoszone ostrzeżenie w referencyjnym wyniku:
  - A kończy poprzednią N o 05:00 w dniu DAY_SHIFT_OFF;
  - zachowanie to jest zgodne z DAY_SHIFT_OFF-01 jako dopuszczalny, lecz gorszy wariant SOFT.

Wniosek architektoniczny:
- CP-SAT jest zweryfikowany jako zdolny do rozwiązania podstawowego rzeczywistego problemu Rota;
- niezależna walidacja HARD jest obowiązkowa również po uzyskaniu FEASIBLE/OPTIMAL od solvera;
- PoC jest referencją zachowania, nie produkcyjną implementacją.

Reguła dla implementera:
- CC NIE MA prawa zastępować tego podejścia własnym solverem, własnym backtrackingiem, własną heurystyką wyszukiwania ani innym silnikiem;
- CC NIE MA prawa zmieniać semantyki sprawdzonych constraints pod pretekstem uproszczenia, optymalizacji, wydajności lub „lepszego modelu”;
- CC może refaktoryzować kod techniczny dopiero wtedy, gdy zachowanie pozostaje identyczne i jest potwierdzone testami kontraktowymi;
- każda propozycja zmiany technologii solvera lub semantyki constraintów jest zmianą architektury/kanonu i wymaga osobnej jawnej decyzji właściciela przed implementacją.

Referencyjny plik PoC:
- `elnath_rota_cp_sat_poc.py`

PoC nie jest automatycznie kodem produkcyjnym. Jego rolą jest:
1. dowód wykonalności wybranej architektury;
2. wzorzec mapowania najważniejszych HARD;
3. fixture porównawczy dla implementacji produkcyjnej;
4. zabezpieczenie przed ponownym projektowaniem solvera przez implementera.

## 6. Frozen behavior PlanningEngine

### 6.0 Literalne reguły operacyjne wymagane przez solver

Poniższe reguły są częścią Frozen Product Contract i nie mogą być zastąpione odwołaniem do innego dokumentu.

SHIFT-01
- standardowa zmiana D: 05:00–17:00;
- standardowa zmiana N: 17:00–05:00 następnego dnia;
- każda wymagana D i N ma dokładnie jednego PRIMARY;
- S nie pokrywa PRIMARY demand.

REST-01
- automatyczny plan musi zapewnić co najmniej 11 godzin nieprzerwanego odpoczynku między końcem jednego Assignment a początkiem następnego Assignment tego samego pracownika;
- oznacza to między innymi, że N kończąca się o 05:00 nie może być bezpośrednio poprzedzona lub zakończona zmianą D zaczynającą się o 05:00 tego samego dnia;
- N→N jest dopuszczalne, ponieważ standardowo daje 12 godzin odpoczynku;
- D→D jest dopuszczalne, ponieważ standardowo daje 12 godzin odpoczynku;
- żadne SOFT ani target_hours nie mogą naruszyć REST-01.

DAY_ONLY-01
- pracownik z DAY_ONLY nie może otrzymać N w automatycznym planowaniu;
- koordynator może świadomie wyłączyć/override tę ochronę;
- solver nie robi tego sam.

DAY_SHIFT_OFF-01
- DAY_SHIFT_OFF oznacza dzień wolny od rozpoczynania pracy;
- w oznaczonym dniu solver nie może rozpocząć ani zmiany D, ani zmiany N;
- zmiana N rozpoczęta poprzedniego dnia może zakończyć się o 05:00 w dniu oznaczonym DAY_SHIFT_OFF;
- takie wejście pracy 00:00–05:00 w dzień wolny jest dopuszczalne, ale stanowi gorszy wariant SOFT;
- jeżeli istnieje porównywalny kandydat zapewniający pełny dzień bez pracy, solver powinien go preferować;
- DAY_SHIFT_OFF nie oznacza UNAVAILABLE_24H.

UNAVAILABLE-01
- UNAVAILABLE_24H blokuje każdy automatyczny Assignment, którego rzeczywisty przedział czasu koliduje z okresem niedostępności.

LEAVE_GRANTED-01
- LEAVE_GRANTED blokuje automatyczny Assignment kolidujący z okresem urlopu;
- użycie pracownika wymaga świadomej decyzji koordynatora/override zgodnie z kontraktem.

LEAVE_PLAN-01
- LEAVE_PLAN nie czyni pracownika nieuprawnionym;
- kolizja jest dopuszczalna tylko jako gorszy wariant SOFT, jeżeli nie istnieje lepszy kandydat;
- kolizja musi być widoczna jako ostrzeżenie.

COVERAGE-01
- wymagane ShiftDemand muszą być pokryte w 100%;
- częściowy grafik nie jest FEASIBLE.

LOAD-01
- dla każdego pracownika należy policzyć każde ruchome okno 7 kolejnych dni kalendarzowych;
- do 60 godzin w takim oknie nie uruchamia bramki tylko z powodu tego progu;
- więcej niż 60 godzin w dowolnym takim oknie nie może być zwykłym FEASIBLE bez jawnej akceptacji koordynatora;
- wynik przed akceptacją to DECISION_REQUIRED z employee, dokładnym oknem i liczbą godzin.

EXTERNAL-01
- X/Y są nieuprawnieni poza aktywnym, potwierdzonym ExternalSupportWindow;
- solver nie otwiera takiego okna i nie używa X/Y samodzielnie.

TARGET-01
- target_hours jest parametrem SOFT;
- solver nie tworzy pracy ani nie narusza HARD tylko po to, aby osiągnąć target.



### 6.1 Normalny wynik
Jeżeli istnieją pełne rozwiązania w ramach aktywnego kontraktu:
- solver zwraca do 1–3 kandydatów;
- każdy kandydat respektuje HARD;
- kandydaci mogą różnić się jakością SOFT;
- koordynator wybiera.

Nie jest wymagane, aby solver zawsze wskazał jeden „jedyny najlepszy” grafik.

### 6.2 HARD
Przykładowe chronione ograniczenia:
- 100% wymaganej obsady D/N;
- brak automatycznego Assignment w LEAVE_GRANTED;
- brak automatycznego Assignment kolidującego z UNAVAILABLE_24H;
- DAY_ONLY blokuje N w normalnym planowaniu;
- X/Y tylko w potwierdzonym ExternalSupportWindow;
- brak tworzenia fikcyjnych zmian tylko po to, by nabić target_hours;
- preserved/frozen/REALIZED/S w REPLAN zgodnie z kontraktem;
- literalne reguły REST-01, LOAD-01 i pozostałe aktywne HARD zapisane w tym Frozen Product Contract.

### 6.3 SOFT
SOFT wpływa na ranking, nie pozwala łamać HARD:
- równomierność godzin;
- preferencje D/N;
- N,N / D,D, jeżeli pozostają dopuszczalne;
- weekend fairness;
- holiday fairness;
- target_hours jako parametr planowania, nie absolutny nakaz.

Weekend fairness:
- im bliżej idealnie równego obciążenia weekendami wśród uprawnionych pracowników, tym lepiej.

Holiday fairness:
- nie jest prawem;
- historia wynika z Assignment + CalendarDay(holiday=true);
- solver preferuje zmniejszanie historycznej nierówności pracy w święta;
- PlanningEngine nie czyta sam CSV/JSON; kalendarz trafia do PlanningState.

### 6.4 Extreme-load gate
Dla każdego pracownika kontrolowane jest każde ruchome okno 7 następujących po sobie dni.

Próg:
- do 60 h w oknie: normalne planowanie;
- >60 h w dowolnym oknie 7 dni: nie jest zwykłym sukcesem solvera.

Jeżeli pełna obsada wymaga przekroczenia progu:
- wynik przechodzi do DECISION_REQUIRED;
- solver wskazuje pracownika, okno dat i obciążenie;
- nie akceptuje sam ekstremalnego wariantu.

### 6.5 DECISION_REQUIRED
DECISION_REQUIRED nie jest awarią.

Oznacza:
- solver doszedł do granicy swojej autonomii;
- normalny kontrakt nie pozwala ukończyć bez decyzji koordynatora.

Wynik musi zawierać:
- nieobsadzony/problematic demand albo constraint powodujący zatrzymanie;
- konkretne blokery;
- możliwe klasy odblokowania;
- skutki każdej klasy, jeśli dają się deterministycznie policzyć.

Przykładowe odblokowania koordynatora:
- potwierdzenie X/Y;
- świadome ściągnięcie pracownika z wolnego;
- świadome odwołanie/override urlopu zgodnie z kontraktem;
- świadome wyłączenie DAY_ONLY;
- świadoma akceptacja >60 h / 7 kolejnych dni;
- inna jawna ręczna korekta przewidziana kontraktem.

Solver nie wybiera i nie aktywuje tych działań sam.

Po decyzji koordynatora:
- PlanningState zostaje zmieniony jawnie;
- planowanie jest uruchamiane ponownie;
- dopiero wtedy solver może zwrócić kandydatów.

### 6.6 TECHNICAL_ERROR
TECHNICAL_ERROR oznacza awarię techniczną:
- błąd modelu;
- błąd procesu;
- nieobsłużony błąd systemowy.

Nie wolno używać TECHNICAL_ERROR jako zastępstwa dla:
- braku obsady;
- konfliktu HARD;
- wymaganej decyzji koordynatora.

## 7. REPLAN

REPLAN jest podstawową ścieżką operacyjną, nie wyjątkiem.

Typowe powody:
- choroba;
- no-show;
- nowa nieobecność;
- zmiana rzeczywistego miesiąca.

REPLAN:
- zachowuje REALIZED;
- zachowuje frozen;
- zachowuje planowane S;
- może redystrybuować przyszłe unfrozen PRIMARY w aktualnym miesiącu;
- nie musi minimalizować liczby zmian względem poprzedniego grafiku, chyba że kontrakt zostanie kiedyś jawnie rozszerzony o taką politykę.

## 8. Szkolenie S

S jest dodatkowe i nie pokrywa PRIMARY demand.

Koordynator:
- wybiera mentora;
- wybiera istniejącą normalną zmianę mentora;
- dodaje S do tej zmiany;
- ustala dokładne godziny S.

Solver:
- nie tworzy autonomicznie S;
- nie przesuwa S przy REPLAN;
- nie powinien automatycznie rozdzielić underlying mentor shift od przypiętego S bez jawnej zmiany tej decyzji.

## 9. Calendar / holidays

CalendarDay zawiera holiday.

Źródło danych świątecznych może być:
- lokalnym deterministycznym kalendarzem;
- trwałymi rekordami;
- bundlowanym plikiem strukturalnym.

PlanningEngine nie otwiera bezpośrednio CSV/JSON.

Warstwa przygotowująca PlanningState:
- rozwiązuje kalendarz;
- dostarcza CalendarDay;
- wyprowadza historię holiday-work z zapisanych Assignmentów.

Nie prowadzi się ręcznego równoległego rejestru „kto pracował w święta”.

## 10. UI — granica na obecnym etapie

Przed stabilizacją domeny i PlanningEngine nie projektujemy szczegółowo finalnego UI.

Zamrożone są wyłącznie wymagane punkty styku:
- prezentacja kandydatów;
- wybór koordynatora;
- DECISION_REQUIRED;
- wyjaśnienie blockerów;
- odblokowania HARD;
- REPLAN;
- ostrzeżenia;
- historia/ocena weekendów i świąt;
- finalizacja i wersje.

Konkretny układ pól i ekranów ma wynikać z rzeczywistych typów domenowych/API, a nie wymuszać backend.

## 11. Mechaniczne wymagania Ward przed wysłaniem tasku do CC

Task MUST mieć:
- contract_version;
- task_id;
- frozen source reference;
- jednoznaczny cel;
- scope modułów/plików;
- wejścia;
- wyjścia;
- obowiązujące reguły;
- reuse directives;
- forbidden actions;
- acceptance checks;
- exact tests expected where known;
- CONTRACT_GAP list.

Backend Ward blokuje task, jeśli:
- wymagany jest wybór między nieuzgodnionymi zachowaniami;
- task odsyła implementera do „samodzielnego uzgodnienia” kilku dokumentów;
- task zawiera otwarte „możesz też...” zmieniające scope;
- nie ma rozróżnienia HARD/SOFT/DECISION;
- implementer mógłby legalnie wypełnić lukę własnym designem;
- nie wiadomo, czy element ma być REUSE / ADAPT / NEW / FORBIDDEN.

## 12. Reguły anty-drift

1. Żaden model nie może przypisać właścicielowi decyzji, której właściciel jawnie nie podjął.
2. PASS Codexa nie jest zgodą produktową.
3. Akceptacja Soneta nie zmienia Frozen Product Contract.
4. CC nie rozszerza tasku.
5. „Lepsza architektura” implementera nie jest powodem do zmiany kontraktu.
6. Test nie definiuje produktu; test weryfikuje kontrakt.
7. Kod zgodny lokalnie, ale sprzeczny z Frozen Product Contract = FAIL kanonu.
8. Materialna niejasność = CONTRACT_GAP, nie inference.
9. Merge/acceptance dotyczy dokładnie audytowanego SHA.
10. Zmiana kanonu wymaga jawnej decyzji właściciela i nowej wersji Frozen Product Contract.

11. Żaden Task Contract nie może zastąpić literalnej reguły solvera zwrotem typu „zgodnie z zasadami czasu pracy” lub „zgodnie ze Spec”; reguła potrzebna implementacji musi być obecna bezpośrednio albo jednoznacznie referencjonowana identyfikatorem Frozen Product Contract.
12. Kandydat FEASIBLE musi przejść niezależną walidację wszystkich HARD po wygenerowaniu, nawet jeżeli ten sam constraint był używany podczas wyszukiwania.

13. Zweryfikowanego PoC CP-SAT nie wolno traktować jako sugestii do ponownego zaprojektowania solvera; jest on technicznym punktem odniesienia dla implementacji.
14. Jeżeli produkcyjna implementacja daje inny status lub narusza HARD dla referencyjnego scenariusza PoC, domyślnym założeniem jest błąd implementacji lub mapowania kontraktu, nie potrzeba zmiany kanonu.
15. Zmiana referencyjnego zachowania wymaga najpierw jawnej zmiany Frozen Product Contract, a dopiero potem zmiany kodu i testów.



## 13. Definition of Done dla pojedynczego tasku

Task jest gotowy dopiero gdy:
1. Mechanical Gate PASS.
2. CC implementuje bez wyjścia poza scope.
3. Testy lokalne tasku PASS.
4. Codex audytuje dokładny SHA i daje werdykt.
5. Sonet wykonuje technical acceptance.
6. Canon Guard sprawdza zgodność z całym produktem.
7. Nie istnieje nierozwiązany CONTRACT_GAP.
8. Jeżeli zmiana dotyka zachowania produktu, właściciel jawnie ją zatwierdził przed zmianą kontraktu.

## 14. Pierwsza kolejność implementacji Rota

Nie zaczynać od pełnego UI.

Preferowana kolejność:
1. Frozen types / domain contract.
2. PlanningState assembly.
3. CP-SAT adapter — minimalne HARD.
4. PlanningResult / DECISION_REQUIRED.
5. SOFT ranking.
6. REPLAN.
7. Calendar + holiday history.
8. Persistence potrzebne do scenariusza end-to-end.
9. Adapter do desktop bridge.
10. Dopiero wtedy szczegółowy UI oparty o rzeczywiste API.

Każdy etap ma być osobnym lub małą grupą Task Contracts.

## 15. Kanoniczna odpowiedzialność

Ward odpowiada przede wszystkim za to, żeby CC nie otrzymał niejednoznacznego zadania.

Codex odpowiada za to, czy implementacja zachowuje się zgodnie z testowanym kontraktem.

Sonet odpowiada za cięcie zadań i lokalną akceptację techniczną.

CC odpowiada za implementację, nie za projektowanie produktu.

Canon Guard odpowiada za wykrycie sytuacji, w której lokalnie poprawne elementy składają się w produkt niezgodny z kanonem.

Właściciel pozostaje jedynym źródłem zgody na materialną zmianę produktu.
