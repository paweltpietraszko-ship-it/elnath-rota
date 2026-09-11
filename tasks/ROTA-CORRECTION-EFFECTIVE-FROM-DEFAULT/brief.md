# ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT — ochrona rozpoczętej służby i jedna data atomowej korekty

STATUS: FINAL PREIMPLEMENTATION RE-CHECK REQUIRED — IMPLEMENTATION HOLD

BASELINE: `main@1198071074b3548727731d78c2f6df48e49f203c`

SOURCE: OWNER_ACCEPTED 2026-09-05 w `arch/PREBRIEF_AUDIT_2026-09-05_T056_FOLLOWUPS.md`, re-audyt `arch/PREBRIEF_REAUDIT_2026-09-05_HISTORICAL_SERVICE_REALIZED.md`, OWNER_CORRECTED 2026-09-11 w BOARD `main@ce97c0ff70921532c7f025124d017af841b9a272`, narrow re-check R1 `task/ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT@7c9366c3325bf7779187a022950c4214d9a2fdbf`.

## 1. Cel

Zamknąć wyłącznie potwierdzone luki istniejącej Korekty ręcznej/historycznej ochrony:

1. klient nie może być ownerem technicznego `effective_from`;
2. zwykła Korekta ręczna może nadal obejmować jedną lub wiele służb w jednej atomowej operacji;
3. po rozpoczęciu służby jej fakty operacyjne nie mogą być swobodnie zmieniane;
4. jedyny wyjątek historyczny to zapisanie po fakcie innego pracownika, który rzeczywiście wykonał całą rozpoczętą służbę, z obowiązkową przyczyną i trwałą historią.

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

## 7. Przelicz Plan / REPLAN / select candidate

Istniejący cutover ma zostać ponownie użyty, nie zastąpiony nowym mechanizmem.

Acceptance-time ochrona musi traktować `start_datetime <= cutover_at` jako rozpoczęte i niezmienne PRIMARY.

Automatyczna ścieżka nie ma wyjątku „faktycznie pracował ktoś inny”. Taki wyjątek jest świadomą Korektą ręczną z przyczyną.

Nie zmieniać solvera ani jego modelu. To guard przed zapisem/akceptacją wyniku.

## 8. UI

`frontend/src/screens/MonthlyPlanning.tsx`:
- nie pokazuje koordynatorowi edytowalnego technicznego `effective_from` dla Korekty ręcznej;
- zwykła korekta może nadal zawierać serię zmian;
- dla rozpoczętego Assignmentu udostępnia wyłącznie zmianę faktycznie pracującej osoby + obowiązkową przyczynę;
- pozostałe akcje historyczne są ukryte/disabled z krótkim wyjaśnieniem;
- UI nie jest granicą bezpieczeństwa — backend odrzuca obejście API.

`frontend/src/api/client.ts` jest obowiązkowym mechanical scope: istniejące trzy metody Korekty ręcznej przestają wymagać i wysyłać klientowe `effective_from`; data pozostaje wyłącznie własnością backendu.

Nie projektować nowego ekranu.

Starsze wersje po starcie są wyłącznie do `Podglądu`; ten Task nie dodaje ani nie zmienia UI restore.

## 9. Acceptance

H1. Atomowa korekta jednej przyszłej służby zapisuje child z `effective_from = recorded_at.date()`, nie z daty tej służby i nie z wartości klienta.

H2. Atomowa korekta wielu przyszłych służb zapisuje jeden child / jedną akcję i jedną datę `effective_from = recorded_at.date()`.

H3. Dokładnie przed początkiem (`now < start`) zwykłe korekty działają.

H4. Dokładnie w chwili początku i po niej (`now >= start`) zmiana kodu/czasu/demandu/state/freeze/NN jest odrzucona.

H5. Rozpoczęty Assignment: zmiana tylko `employee_id` + niepusta przyczyna przechodzi i zostawia trwałe before/after w istniejącej historii.

H6. Ta sama zmiana bez przyczyny jest odrzucona.

H7. Seria zawierająca jeden lub więcej dozwolonych historycznych wyjątków dostaje `effective_from` równy najwcześniejszej dacie początku spośród tych historycznych służb.

H8. Seria z historycznym wyjątkiem nie może przy okazji zmienić żadnego innego chronionego pola rozpoczętej służby.

H9. Bezpośredni endpoint nie może oznaczyć przyszłego PRIMARY jako `REALIZED` ani obejść ochrony historycznej przez własny `effective_from`.

H10. Przelicz Plan/REPLAN/select nie może zmienić Assignmentu z `start_datetime <= acceptance_time`.

H11. Po restarcie/reloadzie aktualny grafik, wydruk i istniejące odczyty rozliczeniowe wskazują pracownika zapisanego jako faktycznie pracujący.

H12. Wewnętrzne oznaczanie zrealizowanego szkolenia TRAINEE nie zostaje złamane.

H13. Istniejące zachowanie starszych wersji jako `Podgląd` po rozpoczęciu pozostaje bez zmian; ten Task nie otwiera restore.

H14. Race/bypass API: jeżeli służba rozpocznie się po otwarciu ekranu, ale przed zapisem, albo request ominie UI, niedozwolona mutacja historyczna jest odrzucona kontrolowanym publicznym błędem z prostym polskim komunikatem; nie wpada w generic/technical unexpected error i nie zapisuje child/current mutation.

## 10. Literalny TASK_SCOPE

Production:
- `rota/application/manual_edit.py` — centralna ochrona korekty, klasyfikacja serii i backendowe wyliczenie jednej daty `effective_from`;
- `rota/application/plan_ops.py` — wyłącznie ujednolicenie cutover `<=` i zachowanie istniejącej ochrony select;
- `rota/application/errors.py` — dedykowany kontrolowany typ odmowy niedozwolonej zmiany rozpoczętej/historycznej służby;
- `api/errors.py` — istniejące publiczne mapowanie tego typu na stały, polski komunikat dla koordynatora;
- `api/routers/manual_edit.py` — tylko marshalling konieczny, aby klient nie był ownerem `effective_from` / historycznego wyjątku;
- `frontend/src/screens/MonthlyPlanning.tsx` — istniejący panel Korekty ręcznej, bez nowego ekranu;
- `frontend/src/api/client.ts` — obowiązkowa mechaniczna korekta trzech obecnych metod Korekty ręcznej po usunięciu klientowego `effective_from`.

Tests:
- nowy wąski `tests/test_historical_service_correction.py`;
- jeden wąski test router/API dla H14: bezpośredni request albo race po starcie służby daje kontrolowaną polską odmowę i nie tworzy zmiany grafiku;
- istniejące testy cutover/manual correction/error mapping mogą być aktualizowane wyłącznie tam, gdzie utrwalają sprzeczną starą granicę lub nowy jawny typ błędu;
- wąski E2E istniejącego panelu Korekty ręcznej, jeśli można go dopisać bez nowej infrastruktury.

Jawnie poza scope:
- `rota/application/lifecycle_ops.py` i restore;
- `api/routers/schedule.py` w części restore;
- jakakolwiek zmiana przywracania starszych wersji;
- `rota/planning/solver.py` i solver rules;
- nowa tabela/rejestr wykonanej pracy;
- zmiana analityki REALIZED, historii świąt lub fairness;
- przebudowa ScheduleVersion lifecycle;
- cross-context Deviation target (osobny Task wykonywany wcześniej);
- print LAW acknowledgement i inne findingi T056.

Jeżeli potrzebna jest nowa production path poza listą, CC zatrzymuje pracę i wraca do architekta.

## 11. Finalny preimplementation re-check Codexa

To ma być wyłącznie literalny re-check korekty R1, bez ponownego otwierania punktów 1–3 z raportu `7c9366c` i bez audytu solvera/lifecycle.

Sprawdzić tylko:
1. czy `rota/application/errors.py` + `api/errors.py` wystarczają jako istniejąca ścieżka kontrolowanej publicznej odmowy dla H14;
2. czy `frontend/src/api/client.ts` jest teraz literalnym, obowiązkowym mechanical scope dla usunięcia klientowego `effective_from`;
3. czy test scope jawnie obejmuje jeden router/API race-or-bypass assertion dla H14;
4. czy po tych trzech poprawkach literalny scope jest kompletny bez nowego workflow/endpointu/ekranu, solvera i restore.

Jeżeli wszystkie cztery = tak: PASS exact SHA i zwolnienie IMPLEMENTATION HOLD. Jeżeli nie: wskazać tylko konkretną brakującą ścieżkę; bez redesignu.