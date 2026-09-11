# ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT — ochrona rozpoczętej służby i data korekty z Assignmentu

STATUS: PREIMPLEMENTATION AUDIT REQUIRED — IMPLEMENTATION HOLD

BASELINE: `main@1198071074b3548727731d78c2f6df48e49f203c`

SOURCE: OWNER_ACCEPTED 2026-09-05 w `arch/PREBRIEF_AUDIT_2026-09-05_T056_FOLLOWUPS.md`, re-audyt `arch/PREBRIEF_REAUDIT_2026-09-05_HISTORICAL_SERVICE_REALIZED.md`, BOARD `ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT` + scope review 2026-09-11.

## 1. Cel

Zamknąć wyłącznie dwie potwierdzone luki istniejącej Korekty ręcznej/historycznej ochrony:

1. korekta konkretnego Assignmentu nie może dostawać technicznego `effective_from` z dzisiejszej daty — data skutku wynika z kalendarzowej daty początku tego Assignmentu;
2. po rozpoczęciu służby jej fakty operacyjne nie mogą być swobodnie zmieniane. Jedyny wyjątek: zapisanie po fakcie innego pracownika, który rzeczywiście wykonał całą służbę, z obowiązkową przyczyną i historią.

Nie tworzymy nowego rejestru wykonanej pracy ani nowego workflow. Wykorzystujemy istniejący Assignment, ScheduleVersion lineage i CoordinatorAction history.

## 2. Jedna granica czasu

Dla PRIMARY:
- `assignment.start_datetime > now` — służba jeszcze się nie rozpoczęła;
- `assignment.start_datetime <= now` — służba rozpoczęta/historyczna i podlega ochronie.

Ta sama semantyka ma obowiązywać Korektę ręczną, akceptację wyniku Przelicz Plan/REPLAN i restore. Nie tworzyć drugiej definicji „rozpoczęta”.

## 3. Służba przed rozpoczęciem

Pozostają obecne operacje korekty planu.

Dla każdej operacji dotyczącej konkretnego Assignmentu:
- backend wylicza `effective_from = assignment.start_datetime.date()`;
- UI może tę datę pokazać informacyjnie, ale koordynator nie ustawia jej ręcznie;
- publiczne API nie może pozwolić na zmianę wyniku przez przesłanie innego `effective_from`.

Dotyczy istniejących operacji tego panelu: zmiana pracownika, kod D6+/N6+, freeze/unfreeze, NN i inne istniejące mutacje Assignmentu.

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
- `effective_from` = data początku Assignmentu;
- istniejąca historia wersji i CoordinatorAction zachowuje before/after, autora i czas korekty;
- po reloadzie, wydruku i w istniejących odczytach rozliczeniowych aktualny grafik wskazuje faktycznie pracującą osobę.

Nie dodawać osobnego typu „actual worker record”, jeśli istniejąca wersja + action trail wystarcza.

## 5. Backend jest ownerem

Blokada nie może żyć tylko w UI.

`rota/application/manual_edit.py::apply_manual_correction` ma przed utworzeniem dziecka porównać upsert z aktualnym Assignmentem i egzekwować powyższą granicę.

Publiczny klient nie może sfabrykować `PRIMARY state=REALIZED` dla przyszłej ani zwykłej służby. Istniejące wewnętrzne użycie `REALIZED` dla szkolenia `TRAINEE` pozostaje poza zmianą.

`REALIZED` może pozostać dodatkowym istniejącym bezpiecznikiem, ale nie jest nowym źródłem prawdy ani wymaganym rozwiązaniem tego Tasku.

## 6. Przelicz Plan / REPLAN / select candidate

Istniejący cutover ma zostać ponownie użyty, nie zastąpiony nowym mechanizmem.

Acceptance-time ochrona musi traktować `start_datetime <= cutover_at` jako rozpoczęte i niezmienne PRIMARY.

Automatyczna ścieżka nie ma wyjątku „faktycznie pracował ktoś inny”. Taki wyjątek jest świadomą Korektą ręczną z przyczyną.

Nie zmieniać solvera ani jego modelu. To guard przed zapisem/akceptacją wyniku.

## 7. Restore

`restore` nie może przestawić current na starszą wersję, jeśli spowodowałoby to zmianę któregokolwiek rozpoczętego PRIMARY względem obecnie obowiązujących faktów.

Przed zmianą current pointer backend porównuje rozpoczęte PRIMARY obecnego current z docelową wersją:
- identyczne fakty historyczne -> restore może działać według istniejących zasad;
- brak Assignmentu albo jakakolwiek różnica chronionych pól/pracownika -> restore odrzucony, current pozostaje bez zmian.

Czytelny komunikat ma wskazać, że rozpoczętej służby nie można cofnąć przez przywrócenie starszego planu i że zmianę faktycznie pracującej osoby robi się przez Korektę ręczną.

Nie tworzyć nowej gałęzi historii ani automatycznej korekty podczas restore.

## 8. UI

`frontend/src/screens/MonthlyPlanning.tsx`:
- dla wybranego przyszłego Assignmentu nie pokazuje edytowalnego technicznego `effective_from`; używa daty Assignmentu;
- dla rozpoczętego Assignmentu udostępnia wyłącznie zmianę faktycznie pracującej osoby + obowiązkową przyczynę;
- pozostałe akcje są ukryte/disabled z krótkim wyjaśnieniem;
- UI nie jest granicą bezpieczeństwa — backend odrzuca obejście API.

Nie projektować nowego ekranu.

## 9. Acceptance

H1. Przyszły Assignment: korekta zapisuje child z `effective_from = start_datetime.date()`, niezależnie od dzisiejszej daty.

H2. Dokładnie przed początkiem (`now < start`) zwykłe korekty działają.

H3. Dokładnie w chwili początku i po niej (`now >= start`) zmiana kodu/czasu/demandu/state/freeze/NN jest odrzucona.

H4. Rozpoczęty Assignment: zmiana tylko `employee_id` + niepusta przyczyna przechodzi i zostawia trwałe before/after w istniejącej historii.

H5. Ta sama zmiana bez przyczyny jest odrzucona.

H6. Bezpośredni endpoint nie może oznaczyć przyszłego PRIMARY jako `REALIZED` ani obejść ochrony historycznej przez własny `effective_from`.

H7. Przelicz Plan/REPLAN/select nie może zmienić Assignmentu z `start_datetime <= acceptance_time`.

H8. Restore starszej wersji nie może cofnąć ani zmienić rozpoczętego Assignmentu; current pozostaje bez zmian.

H9. Restore wersji, która zachowuje wszystkie rozpoczęte fakty identycznie, nadal działa.

H10. Po restarcie/reloadzie aktualny grafik, wydruk i istniejące odczyty rozliczeniowe wskazują pracownika zapisanego jako faktycznie pracujący.

H11. Wewnętrzne oznaczanie zrealizowanego szkolenia TRAINEE nie zostaje złamane.

## 10. Literalny TASK_SCOPE

Production:
- `rota/application/manual_edit.py` — centralna ochrona korekty i wyliczenie daty z Assignmentu;
- `rota/application/plan_ops.py` — wyłącznie ujednolicenie cutover `<=` i zachowanie istniejącej ochrony select;
- `rota/application/lifecycle_ops.py` — guard restore względem rozpoczętych faktów;
- `api/routers/manual_edit.py` — tylko marshalling konieczny, aby klient nie był ownerem effective_from / historycznego wyjątku;
- `api/routers/schedule.py` — tylko jeśli restore wymaga czytelnego istniejącego mapowania błędu bez nowego endpointu;
- `frontend/src/screens/MonthlyPlanning.tsx` — istniejący panel Korekty ręcznej, bez nowego ekranu;
- `frontend/src/api/client.ts` — tylko jeżeli istniejący request type wymaga mechanicznej korekty po usunięciu klientowego effective_from.

Tests:
- nowy wąski `tests/test_historical_service_correction.py`;
- istniejące testy cutover/restore/manual correction mogą być aktualizowane wyłącznie tam, gdzie utrwalają sprzeczną starą granicę;
- wąski E2E istniejącego panelu Korekty ręcznej, jeśli można go dopisać bez nowej infrastruktury.

Poza scope:
- `rota/planning/solver.py` i solver rules;
- nowa tabela/rejestr wykonanej pracy;
- zmiana analityki REALIZED, historii świąt lub fairness;
- przebudowa ScheduleVersion lifecycle;
- cross-context Deviation target (osobny Task wykonywany wcześniej);
- print LAW acknowledgement i inne findingi T056.

Jeżeli potrzebna jest nowa production path poza listą, CC zatrzymuje pracę i wraca do architekta.

## 11. Preimplementation check Codexa

Sprawdzić tylko:
1. czy `apply_manual_correction` jest wystarczającym wspólnym ownerem wszystkich wymienionych ręcznych mutacji bez łamania TRAINING REALIZED;
2. czy istniejący cutover w `plan_ops.py` można ujednolicić do `<=` bez zmiany solvera;
3. czy `lifecycle_ops.restore` ma wszystkie dane do porównania current vs target przed przesunięciem pointera;
4. czy literalny production/test scope jest kompletny.

Jeżeli problem jest mechaniczny — wskazać konkretną brakującą ścieżkę. Bez redesignu i bez nowego rejestru.