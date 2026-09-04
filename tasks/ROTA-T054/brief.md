# ROTA-T054 — trwały wynik PLAN przed zatwierdzeniem

STATUS: READY FOR PREIMPLEMENTATION AUDIT — ZERO KODU PRODUKTU

BASE_MAIN_SHA: `7cd5fde8446bd08a02c647d4eabaab9db200acba`

Źródła:
- `arch/FINDING_2026-09-03_UNACCEPTED_PLAN_PREVIEW.md`
- `arch/ARCHITECT_HANDOFF_UX_BACKLOG_06_08_2026-09-03.md`
- decyzje OWNERA 2026-09-03

## 1. Cel

Po `PLAN`/`REPLAN` koordynator ma móc opuścić ekran albo odświeżyć aplikację i wrócić do dokładnie tego samego niezatwierdzonego wyniku. Ponowne uruchomienie solvera nie jest odtworzeniem wyniku.

Nie zmieniać semantyki zatwierdzonego grafiku i nie tworzyć nowego `ScheduleStatus`, jeżeli nie jest to konieczne.

## 2. Potwierdzony obecny lifecycle

- `plan_month()` tworzy lub wykorzystuje bieżącą `WORKING` ScheduleVersion, ale wynik solvera pozostaje `PlanningResult`.
- `replan()` tworzy `WORKING` child, po czym również zwraca kandydat bez automatycznego zapisu kandydatury.
- dopiero `select_candidate()` waliduje kandydat i wykonuje `replace_working_snapshot()`.
- frontend trzyma returned candidates tylko w React state.

Z tego wynika: preview jest osobnym roboczym artefaktem powiązanym z aktualną `WORKING` version, a nie nowym stanem ScheduleVersion.

## 3. Decyzje OWNERA — zamrożone

1. Trwale pamiętamy jeden ostatni wynik operacji planistycznej dla `(site, month)`.
2. Jeżeli jedna operacja zwróciła kilka wariantów, zachowujemy wszystkie warianty należące do tego jednego wyniku.
3. Kolejny świadomie uruchomiony `PLAN`/`REPLAN` zastępuje poprzedni niezatwierdzony wynik.
4. Przed uruchomieniem kolejnego planowania UI ma jasno poinformować, że poprzedni niezatwierdzony wynik zostanie zastąpiony.
5. Koordynator ma jawny przycisk `Odrzuć wynik`.
6. Akceptacja przez istniejące `select_candidate` usuwa preview dopiero po udanym zapisaniu wybranego grafiku.
7. Odrzucenie usuwa preview, ale nie usuwa/nie mutuje ScheduleVersion history.
8. Przy błędzie trwałego zapisu świeżo policzony wynik może być widoczny w bieżącej sesji, ale UI musi powiedzieć wprost, że wynik nie został zachowany i zniknie po opuszczeniu/odświeżeniu.
9. Przy błędzie odczytu preview zatwierdzony/current schedule pozostaje nietknięty.

## 4. Minimalna architektura

Wprowadzić osobny persisted `PlanPreview`/równoważny rekord roboczy, NIE ScheduleVersion status.

Minimalne dane logiczne:
- `site_id`
- `month`
- `schedule_version_id` — dokładna WORKING version, przeciw której wynik został policzony
- cały wynik potrzebny do ponownego pokazania dokładnie tych samych candidates (wszystkie warianty z jednej operacji)
- warnings/optimization metadata wymagane do wiernego odtworzenia UI
- created_at/operation kind tylko jeśli istniejący UI potrzebuje do czytelnego oznaczenia; nie budować historii preview

Storage ma mieć najwyżej jeden current preview dla `(site_id, month)`.

Nie duplikować algorytmów validatora/solvera w persistence. Preview jest snapshotem wyniku, nie nowym źródłem prawdy o grafiku.

## 5. Lifecycle

### PLAN/REPLAN FEASIBLE
Po otrzymaniu kompletnego FEASIBLE result backend próbuje atomowo zapisać/replace current preview.

Jeśli zapis się uda: API zwraca wynik jako persisted preview.

Jeśli zapis się nie uda: nie mutować ScheduleVersion content kandydatem. Zwrócić kandydat do bieżącej sesji z jednoznaczną informacją dla UI, że preview nie jest trwały. Nie udawać sukcesu persistence.

### Kolejny PLAN/REPLAN
Przed wywołaniem UI ostrzega, że obecny preview zostanie zastąpiony. Po nowym skutecznie zapisanym FEASIBLE preview stary zostaje zastąpiony.

Jeżeli operacja tworzy nową WORKING child (`REPLAN`), preview związany ze starszą version nie może być później prezentowany jako preview nowej version. Audit ma potwierdzić najbezpieczniejszą kolejność invalidation/replace względem istniejącej atomowości lifecycle.

### SELECT CANDIDATE
`select_candidate()` pozostaje jedyną drogą akceptacji. Po pełnym sukcesie `replace_working_snapshot` preview związany z tą wersją jest usuwany w tej samej operacji/commit hooku, aby nie został „duch” zaakceptowanego preview.

Jeśli select kończy się błędem: preview pozostaje.

### ODRZUĆ WYNIK
Nowa mała operacja usuwa current preview dla `(site, month)` po sprawdzeniu kontekstu koordynatora. Nie usuwa ScheduleVersion i nie przywraca historii.

### GET MONTH / reload
Otwieranie miesiąca zwraca current preview, jeśli istnieje i nadal odpowiada current WORKING version. Frontend rekonstruuje ten sam widok kandydatów i oznacza go wyraźnie jako `Niezatwierdzony wynik PLAN`.

Stary preview związany z inną current version jest stale data: nie prezentować go jako aktualnego. Najprościej fail-closed/ignore + cleanup zgodnie z istniejącym stylem persistence.

## 6. UI

- dokładnie ten sam `ScheduleGrid`/candidate UI co po bezpośredniej odpowiedzi PLAN;
- widoczna etykieta `Niezatwierdzony wynik PLAN`;
- istniejący przycisk zatwierdzenia działa przez istniejące `selectCandidate`;
- nowy jawny `Odrzuć wynik`;
- przed nowym PLAN/REPLAN, gdy preview istnieje: proste potwierdzenie, że nowy wynik zastąpi obecny;
- jeśli świeży wynik jest tylko w pamięci przez błąd persistence: komunikat, że po reloadzie/wyjściu zniknie.

Nie tworzyć osobnego ekranu „draft history”.

## 7. Właściciele logiki

- orchestration: `rota/application/plan_ops.py`
- persistence: nowy mały repository lub istniejący repository, jeśli preimplementation audit wykaże naturalnego właściciela; nie wkładać JSON/storage SQL do routera
- schema: istniejący DB/bootstrap/migration owner
- HTTP marshalling: `api/routers/schedule.py`
- UI: `frontend/src/screens/MonthlyPlanning.tsx`

## 8. TASK_SCOPE

Dozwolony kod produktu:
- `rota/application/plan_ops.py`
- `rota/persistence/db.py` lub dokładny istniejący właściciel schema wskazany przez audit
- maksymalnie jeden nowy mały plik persistence dla preview, jeśli brak istniejącego właściwego ownera
- `api/routers/schedule.py`
- `frontend/src/api/client.ts`
- `frontend/src/screens/MonthlyPlanning.tsx`
- ewentualnie `rota/application/open_month.py` tylko jeśli audit wykaże, że to właściwy owner readback zamiast routera

Dozwolone testy/dokumenty:
- `tasks/ROTA-T054/brief.md`
- jeden mały pionowy backend/API test + najmniejszy istniejący test UI

Poza zakresem:
- `ScheduleStatus` enum
- FINAL lifecycle semantics
- History/restore redesign
- solver/validator algorithms
- porównywarka/history wielu preview
- nowy ekran
- automatyczne zatwierdzanie preview

## 9. Acceptance

T54-01: PLAN zwraca FEASIBLE z dwoma candidates; po reloadzie obaj kandydaci są identyczni semantycznie z tymi zwróconymi przez tę samą operację, bez ponownego solver call.

T54-02: przejście na inny ekran i powrót pokazuje ten sam preview z oznaczeniem `Niezatwierdzony wynik PLAN`.

T54-03: przed kolejnym PLAN/REPLAN z istniejącym preview UI informuje, że wynik zostanie zastąpiony; po potwierdzeniu nowy skutecznie zapisany result zastępuje stary.

T54-04: `Odrzuć wynik` usuwa preview; reload go nie przywraca; current ScheduleVersion/history nie są usunięte.

T54-05: wybór kandydata przez istniejący select zapisuje grafik; dopiero po sukcesie preview znika. Błąd select pozostawia preview.

T54-06: błąd persistence świeżego preview nie zapisuje częściowego/duszkowego rekordu i nie modyfikuje working snapshot kandydatem; UI widzi wynik bieżącej sesji oraz komunikat o braku trwałości.

T54-07: błąd odczytu preview nie mutuje ani nie ukrywa zatwierdzonego/current schedule; UI pokazuje błąd preview osobno.

T54-08: preview związany ze starszym `schedule_version_id` nie jest pokazany jako aktualny po zmianie current version.

T54-09: żaden nowy `ScheduleStatus` nie powstaje.

## 10. PREIMPLEMENTATION AUDIT

Audytor przed kodem ma:
- prześledzić exact current `PLAN -> PlanningResult -> select_candidate -> replace_working_snapshot`;
- wskazać konkretny schema/repository owner i atomową granicę zapisu/usuwania preview;
- sprawdzić wpływ REPLAN tworzącego child PRZED solver result na invalidation starego preview;
- sprawdzić, czy `open_month` czy router jest właściwym read ownerem;
- zaproponować najmniejszą reprezentację persistence, bez nowej historii i bez ScheduleStatus.

Audit nie może rozszerzyć produktu o sessions/multi-user locking/history previews. Test nie tworzy kontraktu.

Oczekiwany werdykt: `PASS — READY_FOR_IMPLEMENTATION` albo `FAIL` z konkretną sprzecznością i minimalnym correction proposal.

## 11. EXACT TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-T054/brief.md
- rota/application/plan_ops.py
- rota/application/open_month.py
- rota/persistence/db.py
- rota/persistence/plan_preview_repository.py
- api/routers/schedule.py
- frontend/src/api/client.ts
- frontend/src/screens/MonthlyPlanning.tsx
- frontend/e2e/t054-independent-audit.spec.ts
