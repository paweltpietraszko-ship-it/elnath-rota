# ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID — przeniesienie istniejącej tabeli

STATUS: READY FOR INDEPENDENT PREIMPLEMENTATION CHECK; IMPLEMENTATION HOLD.
DATA: 2026-10-16.
BASE_SHA: 923bd54917a0f9e8512d759611796e9c159fa70a.
Implementer zapisuje rzeczywisty repo_before.hash po obu precheckach
i potwierdza brak zmian objętych symboli względem tej bazy.

## 1. Cel, źródło i granica

Źródło: decyzje OWNERA o mechanicznym refaktorze i rezygnacji z ryzykownych
podziałów, utrwalone w `tasks/ROTA-LARGE-FILES-REFACTOR/brief.md` §1.
PRODUCT_TRUTH zachowania: aktualne kontrakty T031 (tabela), T037 (NN), T052
(S1), T053 (wspólny miesiąc), T065 (ORDINARY) i delegacji, bez ich zmiany.

Wydzielić już istniejący ScheduleGrid, nie rozcinać głównego MonthlyPlanning.
Na bazie planu ScheduleGrid zajmuje linie 77–197; użycia są w liniach
1040 (aktualny grafik), 1441 (historia), 1662 (preview). Numery są wskazówką;
wyrocznią zakresu są nazwy deklaracji i exact base, nie liczenie linii.

Jedyny docelowy moduł produkcyjny:
`frontend/src/screens/monthly-planning/ScheduleGrid.tsx`.
Przenieść dokładnie:
- `ScheduleGrid`, wraz z obecnym kształtem props i własnymi useMemo;
- `daysInMonth`, `hourOf`, `cellLabel`, `assignmentHours`, `totalHours`.

Nowy moduł eksportuje nazwany ScheduleGrid i daysInMonth (ten helper jest
używany również w rodzicu). Pozostałe helpery pozostają lokalne. Używa
obecnych typów z `../../api/client`, bez importu MonthlyPlanning. Parent
importuje oba symbole z `./monthly-planning/ScheduleGrid` i usuwa wyłącznie
ich dawne deklaracje/importy, które po przeniesieniu nie są już używane.
Bez osobnego modułu utils, wrappera komponentu albo nowego kontekstu.

Pozostają w MonthlyPlanning: `firstOfMonthIso`, statusy, formatDateTime,
stripDisplayName, EntryMode i CAŁE ciało głównego komponentu. Nie zmieniać
zależności efektów, kolejności hooków, JSX wywołań ScheduleGrid, props,
kluczy, obsługi requestów/akcji i resetowania zaznaczeń/preview.

## 2. Niezmienniki i redukcja

To jeden istniejący komponent z props, nie projekt nowego podsystemu.
SOURCE: decyzja OWNERA; NECESSITY: naturalna granica renderowania tabeli.
Usunięto potrzebę rozdzielania stanu ekranu i budowania hooka kontrolera,
adaptera API, globalnego store, dodatkowego przekazywania danych lub dużego
pakietu nowych komponentów. Parent nadal ma ponad 600 linii — akceptowane.

Ciała przenoszonych funkcji, ich komentarze i kolejność operacji bez zmian;
dopuszczalne tylko eksporty i importy wymagane lokalizacją. Nie poprawiać
arytmetyki Date/godzin, sortowania, nazw, kodów, pustych komórek ani stylów.
Znalezioną usterkę zgłosić osobno. Nie dostosowywać logiki do nowego modułu.

Dane odczytywane, zapisywane, wysyłane, eksportowane, wygląd tabeli,
interakcje, błąd i powrót do pracy są identyczne z dotychczasową aplikacją.
W szczególności: NN/S1 i D/N vs godziny ORDINARY; osoby tylko z DEL;
pierwszeństwo Assignment przed symbolem DEL; obecne sumowanie godzin;
fallback historycznej listy osób; callback wybierający assignment do korekty.
Nie wprowadzać nowego żądania API ani dodatkowego zapisu przy renderowaniu.

## 3. Dowód i kryteria zakończenia

Przed przeniesieniem zachować dowód bazowego działania celowanych scenariuszy
UI na exact base, w tym porównywalny stan/obrazy tabeli. Dane wyłącznie testowe,
przez istniejące API/setup testów. Nie łączyć niezależnych seedów w nowy
scenariusz biznesowy. Brak środowiska do dowodu istotnej ścieżki → HOLD etapu.

Po przeniesieniu:
1. Manifest stara→nowa deklaracja dla sześciu symboli; porównanie ich ciał
   oraz diffu rodzica. Dowód przeniesienia wspiera testy, nie zastępuje ich.
   Jeśli zmieniło się ciało głównego MonthlyPlanning lub logika helpera,
   cofnąć tę zmianę — nie uzasadniać jej refaktorem.
2. `npm.cmd run build` w frontend; bez nowych zależności lub zmian bundlera.
3. Rzeczywiste UI dla trzech istniejących użyć: aktualny grafik, podgląd
   kandydata i historia. Potwierdzić układ, nazwy, komórki i sumy na tych samych
   danych; w aktualnym grafiku kliknięcie trafia w tę samą korektę osoby/dnia.
   Zmiana miesiąca/obiektu oraz wejście przez „korekta”/„wydruk” zachowują
   obecny stan/przebieg i nie tworzą dodatkowych operacji zapisu.
4. Reuse `frontend/e2e/delegation-schedule-grid.spec.ts` i właściwych przypadków
   `cloud-review-fixes.spec.ts`/`t054-independent-audit.spec.ts`, po sprawdzeniu
   ich rzeczywistego pokrycia. Uzupełnić tylko brakujące trzy użycia/NN/S1/
   ORDINARY w `frontend/e2e/refactor-schedule-grid.spec.ts`. Istniejących
   oczekiwań biznesowych nie zmieniać dla nowej lokalizacji kodu; nie pisać
   testu samego istnienia nowego pliku jako dowodu zachowania.
5. Pełna suita `.venv\Scripts\python.exe -m pytest tests -q` raz przez CC
   na finalnym SHA tego izolowanego etapu, zgodnie z jawną zgodą OWNERA dla
   refaktoru i ryzykiem centralnego ekranu. Backend jest dowodem wspierającym,
   nie dowodem wizualnym. Nie powtarzać pełnej suity automatycznie w Codexie;
   dodatkowy przebieg wymaga uzasadnienia i osobnej zgody.
6. Mechaniczny gate z dosłownym wynikiem i rozliczeniem wyjątku SIZE_FILE
   zgodnie z nadrzędnym planem, niezależny audyt exact SHA, następnie
   ultrareview przed rekomendacją merge. Brak wykonania ultrareview pozostaje
   jawnym HOLD, nie zastępuje się go oświadczeniem autora.

Precheck briefu sprawdza tylko kontrakt/granicę, bez uruchamiania powyższych
testów i bez pełnego audytu produktu. Autor nie daje niezależnego PASS.
FAIL po dostawie wymaga TRACE + OWNERSHIP + niezależnego REPRO na exact SHA.
Nieznane pokrycie to NOT_CHECKED/PARTIAL, bez udawania równoważności.

## 4. Zatrzymanie i wycofanie

STOP zamiast dalszego dzielenia: cykl importów, potrzeba ruszenia stanu/
efektów/akcji rodzica, zmiana kontraktu props lub kształtu danych, brak
możliwości przeniesienia sześciu deklaracji bez zmiany ciała, nieodtworzony
wynik na istotnym użyciu UI, nowy nierozstrzygnięty błąd. Wtedy pozostawić
oryginał, opisać dowód i zakończyć bez wymuszania podziału.
Nie dobierać nowych granic w trakcie implementacji. Powrót: odrzucenie jednego
brancha lub zatwierdzony revert izolowanego commita, bez migracji danych.

OUT_OF_SCOPE: reszta MonthlyPlanning, solver i pozostałe duże pliki;
optymalizacje, nowy stan/hooks/context, UI redesign, arytmetyka godzin/DST,
nowe endpointy, korekty produktu i zmiana oracle testów. Merge i deploy OWNER.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: frontend/src/screens/MonthlyPlanning.tsx --symbol ScheduleGrid; frontend/src/screens/MonthlyPlanning.tsx --symbol daysInMonth
- REASON: sprawdzić kompletne trzy użycia istniejącego komponentu i współdzielony helper dat bez rozcinania stanu ekranu.

Po zamrożeniu zakresu wykonać `python where.py <file>` oraz podane symbole;
po przeniesieniu również nowy plik i te same eksporty. Jeżeli where.py nie
obsługuje TSX, użyć celowanego wyszukania ręcznego i zapisać ograniczenie.
Nie uruchamiać mapy w samym prechecku briefu.

TASK_SCOPE:
- tasks/ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID/brief.md
- tasks/ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID/repo_before.hash
- tasks/ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID/round_01/
- frontend/src/screens/MonthlyPlanning.tsx
- frontend/src/screens/monthly-planning/ScheduleGrid.tsx
- frontend/e2e/refactor-schedule-grid.spec.ts

KONIEC TASK_SCOPE.

Niezależny precheck i ocena merytoryczna CC przed implementacją; nowy raport
`round_01/tests/tests_r<n>.txt`, bez nadpisywania wcześniejszych. Zakończenie
tego Tasku nie zwalnia do kolejnego podziału z tabeli nadrzędnego planu.
