# ROTA-T064 — Kalendarz miesiąca i daty nieobecności

STATUS: PREIMPLEMENTATION AUDIT REQUIRED — IMPLEMENTATION HOLD

BASELINE: `main@021a230989480b07ec0d9a5950ea03591cee098c`

SOURCE: OWNER ruling 2026-09-10 + potwierdzony finding z Royal + inspekcja `Workspace.tsx`, `EmployeeDetail.tsx`, calendar API i durable inputs.

## 1. Cel

T064 naprawia całą potwierdzoną powierzchnię „kalendarz/data”. Nie jest obejściem dla T063.

Po T064 koordynator musi móc:
1. przygotować kalendarz dowolnego wybranego miesiąca roboczego, także przyszłego;
2. wygenerować brakujące dni miesiąca z poprawnym domyślnym rozpoznaniem polskich świąt publicznych;
3. nadal ręcznie skorygować pojedynczy dzień po wygenerowaniu;
4. zgłaszając nieobecność pracownika, otworzyć wybór dat w kontekście aktualnego `workingMonth`, a nie dzisiejszej daty systemowej;
5. widzieć listę nieobecności odnoszącą się do aktualnego `workingMonth`, bez nieoznaczonego mieszania wpisów z innych miesięcy.

T064 ma być ukończone, niezależnie audytowane i przyjęte jako całość przed wykonaniem T063.

## 2. Potwierdzone problemy

### P1 — CalendarModal jest przywiązany do dzisiejszego miesiąca

`frontend/src/screens/Workspace.tsx` wylicza modułowo `today`, `monthStart`, `monthEnd` z `new Date()`. `CalendarModal` nie ma nawigacji miesiąca. Będąc we wrześniu nie można przygotować października.

Obecny „Wygeneruj kalendarz” tworzy brakujące daty jako `holiday=false`, więc program nie zna polskich świąt i koordynator musiałby zaznaczać je ręcznie.

Brak persisted `CalendarDay` dla przyszłego miesiąca może następnie zablokować PLAN przez `IncompleteCalendarData`.

### P2 — AddAbsenceForm nie zna workingMonth

`EmployeeDetail` już otrzymuje `workingMonth`, ale `AddAbsenceForm` go nie dostaje. Używa dwóch surowych `<input type="date">` z pustymi wartościami. Natywny selektor nie jest kontrolowany przez planowany miesiąc.

### P3 — AbsenceLog miesza miesiące

`AbsenceLog` renderuje całe `detail.availability` w kolejności backendu. Nie filtruje ani nie sortuje według `workingMonth`.

## 3. Zamrożone decyzje produktu

1. **T064 jest pełnym zadaniem.** Nie wydzielać minimalnej części kalendarza tylko po to, by uruchomić T063.
2. Kalendarz pozostaje jawnie przygotowywany przez koordynatora; T064 nie wprowadza ukrytego zapisu do bazy podczas zwykłego GET ani podczas PLAN.
3. `CalendarModal` ma własny jawnie wybrany miesiąc `YYYY-MM` i nawigację poprzedni/następny miesiąc. Startowy miesiąc może być bieżący, ale po wyborze przyszłego miesiąca wszystkie odczyty i zapis dotyczą właśnie jego.
4. Generator miesiąca działa w backendzie. Frontend nie posiada własnej listy polskich świąt.
5. Źródłem domyślnej klasyfikacji świąt jest utrzymywana biblioteka Python `holidays`, kalendarz Polski (`PL`), public holidays.
6. Generowanie jest **fill-missing-only**: tworzy tylko brakujące `CalendarDay`. Nigdy nie nadpisuje dnia już zapisanego przez koordynatora. Ręczna korekta pozostaje nadrzędna wobec późniejszego ponownego „generuj”.
7. Po wygenerowaniu miesiąca w bazie istnieje dokładnie jeden `CalendarDay` dla każdej daty miesiąca; święta publiczne PL mają `holiday=true`, pozostałe dni `false`, z zachowaniem wcześniejszych ręcznych wartości.
8. Nie tworzyć osobnej tabeli świąt, własnego algorytmu Wielkanocy ani lokalnej statycznej listy dat świątecznych.
9. Do wyboru zakresu nieobecności użyć aktualnego `@daypicker/react` (DayPicker v10), nie budować własnego kalendarza dat.
10. Date picker nieobecności po otwarciu pokazuje `workingMonth`. Nie ogranicza nieobecności wyłącznie do tego miesiąca — koordynator może przejść do sąsiedniego miesiąca i wybrać zakres przekraczający granicę miesiąca.
11. Po wybraniu zakresu `from/to` do API nadal trafiają istniejące `start_date` / `end_date`; T064 nie zmienia modelu Availability ani semantyki rodzajów nieobecności.
12. `AbsenceLog` pokazuje rekordy, których zakres przecina `workingMonth`: `start_date <= last_day(workingMonth)` i `end_date >= first_day(workingMonth)`. Sortowanie deterministyczne: `start_date`, potem `end_date`, potem `availability_id`.
13. Nagłówek/empty state listy ma jawnie wskazywać miesiąc roboczy, aby użytkownik wiedział jaki zakres ogląda.
14. T064 nie zmienia zasad chorobowego. `SICK_LEAVE` nadal jest rzeczywistą absencją pojawiającą się po fakcie; późniejsze zachowanie PLAN/Przelicz Plan należy do istniejącego lifecycle.
15. T064 nie zmienia solvera, HARD/SOFT, target hours, ScheduleVersion ani logiki T062/T063.

## 4. Generator kalendarza — kontrakt

Nowa operacja ma przyjąć:
- `site_id` — tylko istniejący kontekst autoryzacyjny koordynatora;
- `month` — pierwszy dzień miesiąca w istniejącym stylu ISO (`YYYY-MM-01`) albo jednoznaczne `YYYY-MM`, zgodnie z najprostszym istniejącym API contractem wybranym przez implementera bez zmiany semantyki.

Operacja:
1. waliduje aktywny kontekst koordynatora dla `site_id`;
2. enumeruje wszystkie daty wskazanego miesiąca;
3. pobiera polskie public holidays dla danego roku przez `holidays`;
4. dla każdej daty już istniejącej w `calendar_days` nic nie zmienia;
5. dla każdej brakującej daty zapisuje `CalendarDay(date, holiday=<czy PL public holiday>)`;
6. kończy z kompletnym miesiącem możliwym do odczytu przez istniejący GET `/workspace/calendar?start=...&end=...`.

Nie przenosi holiday rules do frontendu. Nie modyfikuje istniejącego endpointu pojedynczej ręcznej korekty dnia.

### Audyt / trwałość

Kalendarz jest globalnym durable input keyed by date. Generator nie może tworzyć duplikatów ani nadpisywać ręcznej wartości.

Implementer ma użyć istniejącej ścieżki persistence i zachować obecny model audytu/inwalidacji. Jeżeli najprostsza poprawna implementacja batch wymaga jednego nowego cienkiego commandu w `rota/application/durable_inputs.py`, jest to dozwolone; nie tworzyć nowej warstwy domenowej ani nowego repozytorium.

## 5. CalendarModal

`CalendarModal` przestaje korzystać z modułowych `monthStart/monthEnd` wyliczonych raz z `new Date()`.

Ma posiadać lokalny stan wybranego miesiąca i proste sterowanie:
- poprzedni miesiąc;
- nazwa miesiąca + rok;
- następny miesiąc.

Każda zmiana miesiąca przeładowuje istniejący GET zakresu dla pierwszego/ostatniego dnia tego miesiąca.

„Wygeneruj kalendarz” uruchamia nową operację backendową dla wybranego miesiąca i po sukcesie przeładowuje jego dane.

Po pełnym wygenerowaniu nadal można kliknąć pojedynczy dzień i zmienić `holiday` istniejącą ścieżką `setCalendarDay`.

Nie używać `page.clock`, sztucznego `Date.now()` ani zmiany zegara systemowego do obsługi przyszłych miesięcy.

## 6. Nieobecności — date picker

`EmployeeDetail` przekazuje `workingMonth` do `AddAbsenceForm` i `AbsenceLog`.

`AddAbsenceForm`:
- używa DayPicker w trybie zakresu;
- początkowy widoczny miesiąc = `workingMonth`;
- początkowo brak wybranych dat;
- zapis jest możliwy dopiero po wybraniu kompletnego zakresu od/do;
- wybrany zakres jest konwertowany do lokalnych dat ISO bez przesunięcia UTC;
- zachowuje istniejący wybór `kind` oraz istniejące API createAvailability.

Nie tworzyć nowego modelu danych i nie dodawać czasu do dat absencji.

## 7. Lista nieobecności

`AbsenceLog` dostaje `workingMonth`.

Renderuje tylko rekordy przecinające wskazany miesiąc, niezależnie od tego czy zaczęły się wcześniej albo kończą później. Nie przycina rzeczywistych dat wpisu przy prezentacji.

Sortuje deterministycznie po `start_date`, `end_date`, `availability_id`.

Empty state: brak nieobecności **w wybranym miesiącu**, nie globalne „brak zgłoszonych nieobecności”.

T064 nie usuwa historii z backendu; filtr jest wyłącznie kontekstem widoku.

## 8. Technologia

Backend:
- dodać zależność `holidays` do `pyproject.toml`;
- używać publicznego API biblioteki (`country_holidays("PL", years=[year])` lub równoważnego stabilnego API), bez parsowania nazw świąt.

Frontend:
- dodać `@daypicker/react` v10 do dependencies;
- package-lock ma zostać zaktualizowany przez npm;
- dopuszczony import oficjalnego CSS DayPicker albo minimalne dopasowanie w istniejącym `App.css`; nie kopiować kodu biblioteki do repo.

## 9. Acceptance

T64-01 — Z realną datą systemową 2026-09 koordynator może w UI wybrać `2026-10` i wygenerować cały październik bez fake clock.

T64-02 — Po generowaniu liczba persisted CalendarDay dla wybranego miesiąca odpowiada liczbie dni miesiąca; brakujące daty nie pozostają.

T64-03 — Polski public holiday znany bibliotece jest zapisany jako `holiday=true`; zwykły dzień jako `false`.

T64-04 — Ponowne generowanie jest idempotentne i nie nadpisuje ręcznie skorygowanego dnia.

T64-05 — CalendarModal nawiguje co najmniej miesiąc wstecz i wprzód niezależnie od dzisiejszej daty.

T64-06 — Po przygotowaniu przyszłego miesiąca istniejący calendar GET zwraca komplet danych wymagany przez planowanie; brak CalendarDay nie jest skutkiem niemożności wyboru przyszłego miesiąca.

T64-07 — AddAbsenceForm po otwarciu pokazuje `workingMonth`, nie bieżący miesiąc systemowy.

T64-08 — Wybrany range może przekroczyć granicę miesiąca i jest zapisany jako dokładne lokalne ISO `start_date/end_date`.

T64-09 — AbsenceLog dla `workingMonth` pokazuje rekord zaczynający się przed miesiącem i kończący w jego trakcie oraz rekord zaczynający się w miesiącu i kończący po nim.

T64-10 — AbsenceLog nie pokazuje rekordów całkowicie poza `workingMonth` i sortuje wynik deterministycznie.

T64-11 — Zmiana `workingMonth` aktualizuje kontekst date pickera/listy bez użycia dzisiejszej daty jako substytutu.

T64-12 — Istniejące ręczne toggle holiday pojedynczego CalendarDay nadal działa.

T64-13 — Brak zmian solvera, ScheduleVersion, Availability domain semantics, target hours i T062 guidance.

T64-14 — T063 nie dostaje żadnego fake-clock ani test-only bypass; po przyjęciu całego T064 może użyć normalnego produktu do przygotowania października.

## 10. Minimalne testy

Backend/Python:
1. generate future month -> komplet dat;
2. public holiday PL -> true, zwykły dzień -> false;
3. existing manual day survives regenerate unchanged;
4. idempotent second generation;
5. authorization/context remains required.

Frontend/E2E:
1. CalendarModal: z bieżącego miesiąca przejście do przyszłego, generate, reload i pełny miesiąc;
2. ręczna korekta dnia po generate i ponowne generate nie cofa korekty;
3. AddAbsenceForm otwiera DayPicker na `workingMonth`, zapisuje range;
4. AbsenceLog pokazuje tylko zakresy przecinające `workingMonth` i właściwą kolejność.

Nie budować osobnego simulatora dat.

## 11. Literalny TASK_SCOPE do audytu Codexa

Dozwolone production/dependency paths:
- `pyproject.toml`;
- `rota/application/durable_inputs.py` — tylko jeśli potrzebny cienki batch command generatora;
- `api/routers/durable_inputs.py` — endpoint generatora miesiąca;
- `api/routers/calendar.py` — tylko jeśli wymagany jest mały response/read contract; preferować brak zmiany, jeśli istniejący GET wystarcza;
- `frontend/package.json`;
- `frontend/package-lock.json`;
- `frontend/src/api/client.ts`;
- `frontend/src/screens/Workspace.tsx`;
- `frontend/src/screens/EmployeeDetail.tsx`;
- `frontend/src/App.css` — wyłącznie style nowego date pickera/nawigacji miesiąca.

Dozwolone test paths:
- nowy `tests/test_t064.py`;
- nowy `frontend/e2e/t064-calendar-dates.spec.ts`.

Poza scope:
- `rota/planning/**`;
- solver;
- ScheduleVersion/lifecycle;
- `rota/domain.py` i modele Availability/CalendarDay;
- nowe tabele/migracje;
- `frontend/src/screens/MonthlyPlanning.tsx`;
- T063 testy i scenario pack;
- globalny zegar aplikacji;
- `page.clock`/fake clock;
- własny algorytm polskich świąt;
- własny komponent kalendarza zakresu dat.

Jeżeli implementacja wymaga ścieżki spoza tej listy, CC zatrzymuje pracę i wraca do architekta. Nie rozszerza scope samodzielnie.

## 12. Preimplementation audit Codexa

IMPLEMENTATION HOLD.

Codex ma wykonać wąski audyt kontraktu przed kodowaniem:
1. Czy fill-missing-only przez `holidays` zachowuje ręczne korekty i istniejący model CalendarDay/audytu?
2. Czy batch generator da się poprawnie umieścić w dozwolonych `durable_inputs` bez nowej warstwy architektury?
3. Czy `@daypicker/react` v10 można podłączyć do React 18 w obecnym frontendzie bez nowego frameworka UI?
4. Czy `workingMonth` rzeczywiście dociera do EmployeeDetail i wystarczy do AddAbsenceForm/AbsenceLog bez nowego global state?
5. Czy literalny TASK_SCOPE obejmuje wszystkie konieczne ścieżki dependency/build/test?
6. Czy którykolwiek acceptance wymaga zmiany reguł produktu zamiast wyłącznie powierzchni kalendarza/dat?

Codex ma zwrócić PASS albo konkretne luki. Nie implementować przed PASS.