# ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT — ochrona rozpoczętej służby i jedna data atomowej korekty

STATUS: ARCHITECT CORRECTION AFTER R4 — NARROW IMPLEMENTATION ALLOWED

BASELINE: `main@1198071074b3548727731d78c2f6df48e49f203c`

SOURCE: OWNER_ACCEPTED 2026-09-05 w `arch/PREBRIEF_AUDIT_2026-09-05_T056_FOLLOWUPS.md`, re-audyt `arch/PREBRIEF_REAUDIT_2026-09-05_HISTORICAL_SERVICE_REALIZED.md`, OWNER_CORRECTED 2026-09-11 w BOARD `main@ce97c0ff70921532c7f025124d017af841b9a272`, narrow re-check R1 `task/ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT@7c9366c3325bf7779187a022950c4214d9a2fdbf`, R4 FAIL `task/ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT@eff7ec1fc30e2d3ce1596752f1a9c4e49a944521`.

## 1. Cel

Zamknąć wyłącznie potwierdzone luki istniejącej Korekty ręcznej/historycznej ochrony:

1. klient nie może być ownerem technicznego `effective_from`;
2. zwykła Korekta ręczna może nadal obejmować jedną lub wiele służb w jednej atomowej operacji;
3. po rozpoczęciu służby jej fakty operacyjne nie mogą być swobodnie zmieniane;
4. jedyny wyjątek historyczny to zapisanie po fakcie innego pracownika, który rzeczywiście wykonał całą rozpoczętą służbę, z obowiązkową przyczyną i trwałą historią;
5. zapisane historyczne `NN` jest faktem wykonania/nie-wykonania i musi przetrwać późniejsze `Przelicz Plan`/REPLAN bez ponownego układania tej przeszłej służby.

Nie tworzymy nowego rejestru wykonanej pracy ani nowego workflow. Wykorzystujemy istniejący Assignment, ScheduleVersion lineage i CoordinatorAction history.

## 2. Jedna granica czasu

Dla PRIMARY:
- `assignment.start_datetime > now` — służba jeszcze się nie rozpoczęła;
- `assignment.start_datetime <= now` — służba rozpoczęta/historyczna i podlega ochronie.

Ta sama semantyka ma obowiązywać Korektę ręczną i akceptację wyniku Przelicz Plan/REPLAN. Nie tworzyć drugiej definicji „rozpoczęta”.

Starsze wersje grafiku po rozpoczęciu miesiąca pozostają wyłącznie do `Podglądu`. Ten Task nie zmienia ani nie rozszerza restore.

## 3. Zwykła atomowa Korekta ręczna — jedna lub wiele przyszłych służb

Istniejący request-list i jedna atomowa ScheduleVersion/CoordinatorAction pozostają bez zmian co do modelu operacji.

Jeżeli wszystkie zmieniane Assignmenty są jeszcze nierozpoczęte:
- zwykłe istniejące operacje korekty planu pozostają dozwolone;
- korekta może dotyczyć jednej albo wielu służb;
- backend wylicza jedną datę `effective_from` dla całej nowej wersji;
- `effective_from = recorded_at.date()`, gdzie `recorded_at` jest uchwycone raz dla tej atomowej operacji;
- data nie pochodzi z dat przyszłych Assignmentów;
- klient nie podaje i nie wybiera `effective_from`.

Dotyczy istniejących operacji panelu: zmiana pracownika, kod D6+/N6+, freeze/unfreeze, NN i inne istniejące mutacje Assignmentu, o ile dotyczą wyłącznie nierozpoczętych służb.

## 4. Służba rozpoczęta/historyczna

Po `start_datetime <= now` nie wolno zmienić:
- `start_datetime`;
- `end_datetime`;
- `covers_demand_id`;
- `role`;
- `state`;
- `frozen`;
- `operational_code`;
- `work_period_id`;
- `required_rest_after_hours`;
- tożsamości/kształtu służby poza niżej opisanym wyjątkiem pracownika.

### Jedyny wyjątek

Można zmienić wyłącznie `employee_id`, jeżeli koordynator zapisuje osobę, która faktycznie wykonała całą służbę.

Warunki:
- wszystkie pozostałe pola Assignmentu są identyczne jak w obowiązującym zapisie;
- `note` / przyczyna jest obowiązkowa i nie może być pusta;
- istniejąca historia wersji i CoordinatorAction zachowuje before/after, autora oraz `recorded_at` pokazujący kiedy zapisano fakt;
- po reloadzie, wydruku i w istniejących odczytach rozliczeniowych aktualny grafik wskazuje faktycznie pracującą osobę.

Nie dodawać osobnego typu „actual worker record”, jeśli istniejąca wersja + action trail wystarcza.

## 5. Reguła `effective_from` dla serii zawierającej historyczny wyjątek

Jedna atomowa Korekta ręczna może zawierać wiele zmian. Jeżeli zawiera co najmniej jeden dozwolony historyczny zapis faktycznie pracującej osoby:
- `effective_from` całej nowej ScheduleVersion = najwcześniejsza kalendarzowa data początku spośród tych wyjątkowych, rozpoczętych/historycznych służb;
- nie używać dat przyszłych Assignmentów do wyliczenia tej wartości;
- guard z sekcji 4 musi gwarantować, że żadna inna historyczna służba ani inny historyczny fakt nie został zmieniony;
- przyszłe zmiany zawarte w tej samej atomowej operacji pozostają zwykłymi przyszłymi korektami, ale dziedziczą tę jedną wersyjną datę zgodnie z istniejącym modelem lineage.

Klient nadal nie podaje `effective_from`.

## 6. Backend jest ownerem

Blokada nie może żyć tylko w UI.

`rota/application/manual_edit.py::apply_manual_correction` ma przed utworzeniem dziecka:
- porównać każdy upsert z aktualnym Assignmentem;
- sklasyfikować go jako przyszły albo rozpoczęty/historyczny według jednej granicy czasu;
- odrzucić każdą niedozwoloną zmianę historyczną;
- rozpoznać dozwolony wyjątek `employee_id` + obowiązkowa przyczyna;
- wyliczyć jedną backendową datę `effective_from` całej operacji zgodnie z sekcjami 3 i 5;
- uchwycić jeden `recorded_at` dla spójnej historii tej atomowej operacji.

Odrzucenie próby niedozwolonej zmiany rozpoczętej/historycznej służby jest kontrolowanym wynikiem biznesowym, nie awarią techniczną:
- `rota/application/errors.py` ma posiadać dedykowany typ wyjątku dla tej odmowy;
- `api/errors.py`, jako istniejący owner publicznego mapowania błędów po T060, mapuje go na stały, prosty polski komunikat dla koordynatora;
- komunikat nie może ujawniać tracebacku, identyfikatorów technicznych ani sugerować „nieoczekiwanej awarii”;
- nie tworzyć nowego endpointu ani równoległego systemu błędów.

Publiczny klient nie może sfabrykować `PRIMARY state=REALIZED` dla przyszłej ani zwykłej służby. Istniejące wewnętrzne użycie `REALIZED` dla szkolenia `TRAINEE` pozostaje poza zmianą.

`REALIZED` może pozostać dodatkowym istniejącym bezpiecznikiem, ale nie jest nowym źródłem prawdy ani wymaganym rozwiązaniem tego Tasku.

## 7. Przelicz Plan / REPLAN / select candidate — w tym historyczne NN

Istniejący cutover pozostaje ownerem ochrony przy akceptacji wyniku. Acceptance-time ochrona musi traktować `start_datetime <= cutover_at` jako rozpoczęte fakty PRIMARY.

R4 ujawnił szczególny przypadek, którego poprzedni scope nie obejjmował poprawnie: po zapisaniu historycznego `NN` istniejący Assignment jest `PRIMARY + CANCELLED + operational_code=NN`. Taki wpis nie oznacza pracy ani pokrycia, ale jest trwałym faktem historycznym.

Zamrożony wynik:
- `Przelicz Plan`/REPLAN nie może usunąć, przepisać ani zastąpić rozpoczętego `PRIMARY+CANCELLED+NN`;
- przeszły demand związany z takim NN nie jest ponownie obsadzany przez automat po fakcie;
- dokładny historyczny Assignment NN przechodzi do zaakceptowanego dziecka jako fakt;
- NN nadal **nie** liczy się jako wykonana praca, pokrycie, zajętość, godziny TARGET/fairness ani odpoczynek;
- automat rozwiązuje wyłącznie część planu, która nadal jest planem, nie przepisuje historii.

Dozwolone jest wąskie użycie `rota/planning/solver.py` wyłącznie do przeniesienia/ochrony historycznego NN w istniejącym pionie solve-output. Nie wolno zmieniać reguł kwalifikacji, objective, fairness, limitów ani semantyki przyszłych CANCELLED.

`rota/application/plan_ops.py` musi równolegle egzekwować acceptance guard także dla rozpoczętego `PRIMARY+CANCELLED+NN`: brak wpisu, zmiana jego pól albo rewrite pod tym samym `assignment_id` jako inny stan/pracownik jest odrzucany.

Automatyczna ścieżka nie ma wyjątku „faktycznie pracował ktoś inny”. Taki wyjątek jest świadomą Korektą ręczną z przyczyną.

## 8. UI

`frontend/src/screens/MonthlyPlanning.tsx`:
- nie pokazuje koordynatorowi edytowalnego technicznego `effective_from` dla Korekty ręcznej;
- zwykła korekta może nadal zawierać serię zmian;
- dla rozpoczętego Assignmentu udostępnia wyłącznie zmianę faktycznie pracującej osoby + obowiązkową przyczynę oraz istniejącą akcję NN, jeżeli jest dostępna;
- pozostałe akcje historyczne są ukryte/disabled z krótkim wyjaśnieniem;
- UI nie jest granicą bezpieczeństwa — backend odrzuca obejście API.

`frontend/src/api/client.ts` jest obowiązkowym mechanical scope: istniejące trzy metody Korekty ręcznej przestają wymagać i wysyłać klientowe `effective_from`; data pozostaje wyłącznie własnością backendu.

Nie projektować nowego ekranu.

Starsze wersje po starcie są wyłącznie do `Podglądu`; ten Task nie dodaje ani nie zmienia UI restore.

## 9. Acceptance

H1. Atomowa korekta jednej przyszłej służby zapisuje child z `effective_from = recorded_at.date()`, nie z daty tej służby i nie z wartości klienta.

H2. Atomowa korekta wielu przyszłych służb zapisuje jeden child / jedną akcję i jedną datę `effective_from = recorded_at.date()`.

H3. Dokładnie przed początkiem (`now < start`) zwykłe korekty działają.

H4. Dokładnie w chwili początku i po niej (`now >= start`) zwykła zmiana kodu/czasu/demandu/state/freeze jest odrzucona; istniejąca jawna akcja NN pozostaje dozwolonym zapisem faktu nieprzepracowania.

H5. Rozpoczęty Assignment: zmiana tylko `employee_id` + niepusta przyczyna przechodzi i zostawia trwałe before/after w istniejącej historii.

H6. Ta sama zmiana bez przyczyny jest odrzucona.

H7. Seria zawierająca jeden lub więcej dozwolonych historycznych wyjątków dostaje `effective_from` równy najwcześniejszej dacie początku spośród tych historycznych służb.

H8. Seria z historycznym wyjątkiem nie może przy okazji zmienić żadnego innego chronionego pola rozpoczętej służby.

H9. Bezpośredni endpoint nie może oznaczyć przyszłego PRIMARY jako `REALIZED` ani obejść ochrony historycznej przez własny `effective_from`.

H10. Przelicz Plan/REPLAN/select nie może zmienić żadnego rozpoczętego faktu PRIMARY, w tym `PRIMARY+CANCELLED+NN`.

H10a. Po realnym historycznym NN -> `Przelicz Plan` -> akceptacja: dokładny wpis NN pozostaje w child/current, nie liczy się jako praca/pokrycie i jego przeszły demand nie zostaje automatycznie ponownie obsadzony.

H10b. Acceptance guard odrzuca kandydat, który usuwa historyczne NN albo pod tym samym `assignment_id` zamienia je na PLANNED/innego pracownika.

H11. Po restarcie/reloadzie aktualny grafik, wydruk i istniejące odczyty rozliczeniowe wskazują pracownika zapisanego jako faktycznie pracujący albo zachowują zapis historycznego NN.

H12. Wewnętrzne oznaczanie zrealizowanego szkolenia TRAINEE nie zostaje złamane.

H13. Istniejące zachowanie starszych wersji jako `Podgląd` po rozpoczęciu pozostaje bez zmian; ten Task nie otwiera restore.

H14. Race/bypass API: jeżeli służba rozpocznie się po otwarciu ekranu, ale przed zapisem, albo request ominie UI, niedozwolona mutacja historyczna jest odrzucona kontrolowanym publicznym błędem z prostym polskim komunikatem; nie wpada w generic/technical unexpected error i nie zapisuje child/current mutation.

## 10. Literalny TASK_SCOPE

Production:
- `rota/application/manual_edit.py` — centralna ochrona korekty, klasyfikacja serii i backendowe wyliczenie jednej daty `effective_from`;
- `rota/application/plan_ops.py` — cutover `<=`, ochrona wszystkich rozpoczętych PRIMARY przy acceptance, w tym historycznego `PRIMARY+CANCELLED+NN`;
- `rota/planning/solver.py` — **wyłącznie** minimalne zachowanie historycznego `PRIMARY+CANCELLED+NN` przez Przelicz Plan/REPLAN tak, aby nie był re-solved jako przeszłe pokrycie i wracał w kandydacie jako niepracujący fakt; bez zmian eligibility/objective/fairness/HARD dla przyszłości;
- `rota/application/errors.py` — dedykowany kontrolowany typ odmowy niedozwolonej zmiany rozpoczętej/historycznej służby;
- `api/errors.py` — istniejące publiczne mapowanie tego typu na stały, polski komunikat dla koordynatora;
- `api/routers/manual_edit.py` — tylko marshalling konieczny, aby klient nie był ownerem `effective_from` / historycznego wyjątku;
- `frontend/src/screens/MonthlyPlanning.tsx` — istniejący panel Korekty ręcznej, bez nowego ekranu;
- `frontend/src/api/client.ts` — obowiązkowa mechaniczna korekta trzech obecnych metod Korekty ręcznej po usunięciu klientowego `effective_from`.

Tests:
- `tests/test_historical_service_correction.py`;
- istniejący `tasks/ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT/round_01/tests/audit_r3_repro.py` pozostaje obowiązkowym reproduktorem R3-01/R3-02;
- jeden wąski test router/API dla H14;
- istniejące testy cutover/manual correction/error mapping mogą być aktualizowane wyłącznie tam, gdzie utrwalają sprzeczną starą granicę lub nowy jawny typ błędu;
- wąski E2E istniejącego panelu Korekty ręcznej, jeśli można go dopisać bez nowej infrastruktury.

Jawnie poza scope:
- `rota/application/lifecycle_ops.py` i restore;
- `api/routers/schedule.py` w części restore;
- jakakolwiek zmiana przywracania starszych wersji;
- nowe solver rules, zmiana eligibility/objective/fairness/limitów lub budżetu;
- nowa tabela/rejestr wykonanej pracy;
- zmiana analityki REALIZED, historii świąt lub fairness poza koniecznym brakiem liczenia NN jako pracy;
- przebudowa ScheduleVersion lifecycle;
- cross-context Deviation target;
- print LAW acknowledgement i inne findingi T056.

Jeżeli rozwiązanie wymaga production path poza powyższą listą albo zmiany semantyki solvera wykraczającej poza historyczne NN, CC zatrzymuje pracę i wraca do architekta.

## 11. Następny re-check Codexa

Po implementacji poprawki R3-02 wykonać wyłącznie wąski re-check:
1. trzy retained tests z `audit_r3_repro.py` muszą być PASS;
2. sprawdzić, że historyczne NN pozostaje w zaakceptowanym child/current po `Przelicz Plan`;
3. sprawdzić, że jego przeszły demand nie jest re-solved i NN nie jest liczone jako work/coverage/fairness/REST;
4. potwierdzić, że diff w `solver.py` nie zmienia zachowania przyszłych CANCELLED ani innych solver rules;
5. bez ponownego pełnego audytu solvera, bez symulatorów i legacy benchmarków.
