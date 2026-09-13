# ROTA-T065-MANUAL-MIDDLE-SHIFT — ręczna dodatkowa praca ORDINARY („środek”)

STATUS: PREIMPLEMENTATION — IMPLEMENTATION HOLD UNTIL CODEX PASS

DEPENDENCIES:
- `ROTA-T065-CONFIGURABLE-ROLES` — wykonywana praca musi wskazywać obowiązkową rolę z katalogu Site, ale nie zmienia stanowiska pracownika;
- `ROTA-T065-ORDINARY-TIME-AVAILABILITY` — jeśli zostanie wdrożone wcześniej, ręczny środek musi korzystać z tego samego oracla dostępności godzinowej.

SOURCE:
- finding Codexa `ROTA-T065-PANEL-CLEANUP` część B
- OWNER correction: „zmiana ruchoma/środek” to sezonowa/eventowa dodatkowa realna praca, dodawana wyłącznie ręcznie
- istniejący `apply_manual_correction`, ScheduleVersion child, validator, deviations, action trail

## 1. Cel

Umożliwić koordynatorowi dodanie do istniejącego grafiku ORDINARY dodatkowej realnej pracy w dowolnym przedziale godzinowym, np. sezonowego/eventowego „środka”, bez dodawania jej do stałego katalogu i bez angażowania solvera.

Przykład: normalne pokrycie 05:00–12:00 i 12:00–19:00, a w konkretnym dniu koordynator ręcznie dodaje dodatkową osobę 10:00–16:00.

## 2. To jest Manual Correction, nie planowanie

„Środek”:
- nie jest `StandardShift`;
- nie generuje `ShiftDemand` dla przyszłych dni;
- nie jest pracą solvera;
- nie powoduje nowego PLAN/REPLAN;
- nie tworzy drugiego generatora;
- nie tworzy specjalnego pipeline'u sklepowego.

Ma przejść przez istniejący `apply_manual_correction` i stworzyć normalny child `ScheduleVersion` z istniejącym audytem/deviations.

## 3. Realna praca, bez zwolnień S1

Ręczny „środek” jest normalną pracą.

Nie wolno modelować go jako `PERIODIC_TRAINING/S1`, ponieważ S1 ma specjalne zwolnienia REST/WEEKLY-REST i semantykę szkolenia.

Środek uczestniczy normalnie w:
- overlap;
- odpoczynku dobowym;
- odpoczynku tygodniowym;
- czasie/obciążeniu pracy;
- availability;
- cross-site constraints;
- innych istniejących HARD-ach właściwych dla ORDINARY.

Jeżeli koordynator świadomie narusza regułę, używa istniejącego deviation/override lifecycle; nie tworzyć nowego wyjątku.

## 4. Rola wykonywanej pracy jest obowiązkowa

Każdy ręczny środek ORDINARY musi wskazać rolę wykonywanej pracy z katalogu tego Site.

To jest **rola tej konkretnej pracy**, nie stanowisko pracownika.

Przykład:
- stanowisko osoby: `Kierownik`;
- ręczna praca: `Sprzedawca`, 10:00–16:00;
- po zapisie osoba nadal jest prezentowana jako `Kierownik`.

Jeżeli pracownik nie jest dopuszczony do pokrycia tej roli przez reguły z `ROTA-T065-CONFIGURABLE-ROLES`, validator zgłasza naruszenie; UI nie może cicho nadać mu drugiego stanowiska.

## 5. Persistence/history — reuse Assignment/ScheduleVersion

Nie tworzyć osobnej tabeli `middle_shifts` jako równoległej historii grafiku.

Ręczna praca ma być zapisana w istniejącym snapshotcie ScheduleVersion jako Assignment.

Ponieważ taki Assignment nie pokrywa `ShiftDemand`, musi mieć trwały snapshot roli wykonywanej pracy w istniejącym modelu Assignment lub innym minimalnym ownerze powiązanym z Assignment. Nie wolno użyć do tego `Assignment.role`, bo ten enum oznacza `PRIMARY/TRAINEE/PERIODIC_TRAINING`, a nie rolę biznesową.

Codex ma sfalsyfikować minimalne miejsce pola przed implementacją, ale kontrakt jest twardy: historyczna rola tej pracy nie może zależeć od późniejszej konfiguracji Site.

## 6. UI

W istniejącej sekcji `Ręczna korekta` dla ORDINARY dodać operację typu `Dodaj pracę` / `Dodaj środek`.

Minimalne dane wejściowe:
- pracownik;
- data;
- godzina od;
- godzina do / przejście przez północ jeśli wspiera to istniejący kontrakt czasu;
- rola wykonywanej pracy z katalogu Site;
- opcjonalna notatka.

Nie dodawać tej operacji do katalogu stałych zmian.

Nie używać D/N/1/2/3 jako źródła godzin ani roli.

## 7. Eligibility/validation

Ręczny środek nie jest automatycznie blokowany przed zapisem przez osobny sklepowy gate. Ma wejść do istniejącego validatora Manual Correction tak jak inna realna Assignment.

Validator musi widzieć:
- rzeczywisty interval;
- pracownika;
- wykonywaną rolę;
- istniejące availability;
- pozostałą pracę tego pracownika w Site i cross-site.

Jedna wspólna semantyka z automatycznym planowaniem; zero kopiowania reguł prawa pracy.

## 8. Coverage

Ręczny środek jest dodatkową pracą i domyślnie nie zmienia definicji stałego demandu katalogowego ani jego required_count.

Jeżeli jego interval/rola faktycznie pokrywa istniejący demand, nie wolno automatycznie przepisywać demandu ani tworzyć nowej semantyki coverage bez osobnego kontraktu. Ten Task dotyczy dodania realnej dodatkowej pracy, nie przebudowy modelu demand coverage.

## 9. Print/history

Historyczny ekran i przyszły ORDINARY PDF muszą móc pokazać tę pracę przez rzeczywiste godziny i rolę wykonywanej pracy.

Nie wolno na tej podstawie zmieniać stanowiska pracownika.

`ROTA-T065-PRINT-GAP` pozostaje właścicielem layoutu PDF.

## 10. Acceptance — minimum

1. Koordynator dodaje ręcznie 10:00–16:00 dla konkretnego dnia bez zmiany katalogu i bez uruchamiania solvera.
2. Zapis tworzy child ScheduleVersion przez istniejący manual-correction lifecycle.
3. Praca uczestniczy w normalnych REST/load/overlap/availability checks i nie korzysta ze zwolnień S1.
4. Praca ma obowiązkową rolę biznesową Site, ale nie zmienia stanowiska pracownika.
5. Brak dopuszczenia do wskazanej roli jest widoczny w istniejącym validation/deviation flow, a nie naprawiany automatycznie.
6. Historyczny reload zachowuje godziny i rolę konkretnej pracy po późniejszej edycji katalogu ról.
7. OCHRONA i S1 regression unchanged.

TASK_SCOPE:
- rota/domain.py
- rota/persistence/schema.py
- rota/persistence/schedule_repository.py
- rota/application/manual_edit.py
- rota/planning/validator.py
- api/routers/manual_edit.py
- api/routers/schedule.py
- frontend/src/screens/MonthlyPlanning.tsx
- frontend/src/api/client.ts
- tests/

## 11. HOLD

IMPLEMENTATION HOLD do preimplementation PASS Codexa na dokładnym SHA tego briefu.
