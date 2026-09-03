# ROTA-T047 — wydruk istniejących zmian i dużej obsady

STATUS: PROPOZYCJA DO WERYFIKACJI CC — ZERO KODU PRODUKTU — IMPLEMENTACJA
DOPIERO PO PASS PREIMPLEMENTATION AUDIT

BASE_MAIN_SHA: `6ff5b827ed1530bb3fc4370727fa1e3784269926`

Źródło: ręczna próba czterech realnych obiektów ochrony opisana w
`manual_trials/Ochrona_2026-09/RAPORT.md` na
`manual/ochrona-scenarios@53722e3`. Próba przeszła przez produkcyjne operacje
backendu, `PLAN`, wybór kandydata i eksport. Nie tworzyła ręcznie demandów ani
Assignmentów.

## 1. Cel

Naprawić dwa potwierdzone problemy produkcyjnego PDF:

1. Rota pozwala skonfigurować istniejące kody pracy D/N o długości 2 h, 4 h
   i 16 h, ale odrzuca taki prawidłowy grafik jako
   `UNSUPPORTED_SHIFT_KIND`.
2. Rota odmawia wydruku grafiku licznej, lecz zwyczajnej obsady, jeżeli jej
   wiersze nie mieszczą się na jednej stronie A3. W próbie Parku
   Logistycznego dotyczyło to 17 LOCAL.

Po T047 koordynator ma otrzymać czytelny PDF również w obu tych przypadkach.
Nie zmieniamy grafiku, danych obiektu ani wyniku solvera tylko po to, aby
zmieściły się w wydruku.

## 2. Potwierdzona przyczyna: kody 2/4/16 h

`rota/persistence/site_repository.py::FROZEN_WORK_CODE_HOURS` już zawiera
między innymi:

- `D2 = 4 h`;
- `D4 = 2 h`;
- `N2 = 16 h`.

Ustawienia wydruku pozwalają przypisać tym kodom dokładne przedziały czasu.
`schedule_export.py::_map_work_code` potrafi je dopasować po rodzinie D/N,
czasie początku, czasie końca, przejściu przez północ i długości.

Eksport nie dochodzi jednak do tego dopasowania. `_validate_item` wcześniej
odrzuca każdy demand z `catalog_kind == OTHER`. Katalog oznacza w ten sposób
również prawidłowe zmiany inne niż 12 h i 24 h. W realnej próbie odrzucono
przez to skonfigurowane N2=16 h oraz D2=4 h.

### Wymagane zachowanie

- Assignment rodziny D albo N, którego rzeczywisty przedział jest zgodny z
  demandem i ma dokładne dopasowanie w zapisanych ustawieniach wydruku, jest
  drukowany wskazanym kodem również wtedy, gdy `catalog_kind == OTHER`.
- Samo `OTHER` nie oznacza błędu wydruku. O drukowalności rozstrzyga istniejące
  dokładne mapowanie D/N w `_map_work_code`.
- Jeśli żaden skonfigurowany kod nie odpowiada dokładnie przedziałowi, eksport
  nadal zatrzymuje się istniejącym problemem `WORK_CODE_MAPPING_REQUIRED`.
  Nie wolno wybierać kodu tylko na podstawie zbliżonej liczby godzin.
- `TRAINEE`, brak provenance, sprzeczny przedział oraz rzeczywiście
  nieobsługiwany rodzaj pracy zachowują dotychczasowe bezpieczne odmowy.
- Składanie prawidłowej zmiany 24 h oraz sposób druku nieobecności pozostają
  bez zmian.

T047 nie dodaje nowego kodu 14 h. Zamrożona legenda go nie zawiera, a OWNER
nie zlecił jej rozszerzenia. Taki przedział nadal ma zakończyć się
`WORK_CODE_MAPPING_REQUIRED`, dopóki nie zapadnie osobna decyzja produktowa.

## 3. Wydruk wielostronicowy

Obecne `_check_fits` i `_render_pdf` zakładają jeden arkusz. Gdy pary wierszy
PLAN/WYK nie mieszczą się przy minimalnej czytelnej wysokości, eksport zwraca
`ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT`.

### Wymagane zachowanie

- PDF nadal używa poziomego A3 i pokazuje wszystkie dni miesiąca na każdej
  stronie.
- Wiersze pracowników są dzielone pionowo na tyle stron, ile potrzeba.
- Para PLAN/WYK jednego pracownika zawsze pozostaje razem; pracownika nie
  wolno przeciąć między stronami ani powtórzyć.
- Na każdej stronie należy powtórzyć nazwę firmy i obiektu, okres i prawdziwy
  zakres dat, informację o pochodzeniu/wersji grafiku, nagłówki dni oraz
  nagłówki kolumn podsumowania.
- Strony mają numerację `strona X z Y`.
- Legenda ma być obecna w dokumencie co najmniej raz. Nie musi być powtarzana
  na każdej stronie.
- Nie wolno zmniejszać tekstu lub wysokości wiersza poniżej obecnego minimum
  tylko po to, aby wymusić jedną stronę.
- Kontrola zbyt długich nazw/nagłówków pozostaje fail-closed. T047 usuwa
  odmowę wynikającą z samej liczby pracowników, nie z tekstu, którego nie da
  się czytelnie zmieścić.
- Lista osób na PDF pozostaje ustalana przez obecny eksport. Task nie zmienia
  zasad LOCAL/EXTERNAL_SUPPORT ani obsady.

Kontrola odbiorcza: produkcyjny eksport Parku Logistycznego z próby, mającego
17 LOCAL, ma zwrócić wielostronicowy PDF zawierający wszystkich 17
pracowników dokładnie raz i bez uciętych par PLAN/WYK.

## 4. Co już istnieje i nie może zostać zdublowane

Ekran `frontend/src/screens/Export.tsx` już wykonuje jeden eksport, tworzy z
otrzymanych bajtów podgląd PDF w `iframe`, a przycisk „Pobierz” zapisuje ten
sam `Blob`. T047 nie tworzy nowego podglądu, drugiego eksportu, endpointu ani
modelu odpowiedzi. Po naprawie backendowego PDF istniejący podgląd zacznie
działać także dla tych grafików.

Ograniczenie wprowadzania zmian wyłącznie o pełnej godzinie jest problemem
wejścia/katalogu, a nie wydruku. Zostaje do osobnego zadania UX. Tak samo poza
T047 pozostają komunikaty i prowadzenie użytkownika po decyzjach solvera.

## 5. PREIMPLEMENTATION REDUCTION GATE

| Element | Źródło | Minimalna konieczna zmiana |
|---|---|---|
| druk kodów 2/4/16 h | realne odmowy Placu i Urzędu + istniejąca legenda | usunąć przedwczesną odmowę `OTHER`; pozostawić dokładne mapowanie w obecnym ownerze eksportu |
| duża obsada | realna odmowa Parku przy 17 LOCAL | podzielić istniejącą tabelę na strony w obecnym rendererze |
| test mapowania | sprzeczność ustawień z eksportem | celowane przypadki istniejących kodów i brak dopasowania |
| test paginacji | utrata całego PDF dla dużej obsady | tekst i render wszystkich stron rzeczywistego PDF |

Usunięte z propozycji jako zbędne: nowy endpoint, nowe DTO, nowy ekran
podglądu, drugi generator PDF, zmiany solvera, zmiany katalogu zmian,
rozbudowa legendy o 14 h, role/stanowiska/kwalifikacje, zmiany modelu kadrowego
i ogólny refaktor eksportu.

## 6. TASK_SCOPE

Dozwolony kod produktu:

- `rota/application/schedule_export.py`

Dozwolone testy i dokumenty:

- `tasks/ROTA-T047/brief.md`;
- `tests/test_t020.py`;
- jeden nowy celowany plik testowy T047 wyłącznie wtedy, gdy rozdzielenie
  przypadków od rozbudowanego `test_t020.py` rzeczywiście upraszcza test.

Każdy inny plik produktu wymaga zatrzymania i wskazania konkretnej
konieczności przed edycją. W szczególności poza zakresem są:

- `frontend/**` i `api/**`;
- `rota/planning/**`, solver, walidator grafiku i fairness;
- `rota/persistence/site_repository.py` oraz zmiana zamrożonych wartości
  kodów;
- katalog zmian i obsługa wejścia co 30 minut;
- obsada, target hours, LOCAL/EXTERNAL_SUPPORT;
- nieobecności i ich oznaczenia.

## 7. WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS:
  - `rota/application/schedule_export.py --symbol _validate_item`
  - `rota/application/schedule_export.py --symbol _map_work_code`
  - `rota/application/schedule_export.py --symbol _check_fits`
  - `rota/application/schedule_export.py --symbol _render_pdf`
- REASON: Task zmienia istniejącego ownera kwalifikacji danych do wydruku i
  znosi założenie jednej strony; trzeba potwierdzić wszystkich rzeczywistych
  callerów bez tworzenia drugiej ścieżki.

Wykonane na `BASE_MAIN_SHA`: każdy z czterech symboli ma jedną definicję;
`_validate_item`, `_map_work_code` i `_check_fits` mają po jednym produkcyjnym
callerze w tym samym module, a `_render_pdf` jest wołane przez obecny eksport.
Raw hits nie są werdyktem ownership — kod został przeczytany na exact SHA.

## 8. Macierz odbioru

- **T47-01 — D2/4 h:** prawidłowy Assignment D 4 h, zgodny z demandem i
  ustawieniem D2, drukuje `D2`; nie zwraca `UNSUPPORTED_SHIFT_KIND`.
- **T47-02 — D4/2 h:** analogicznie prawidłowy przedział 2 h drukuje `D4`.
- **T47-03 — N2/16 h:** prawidłowa zmiana nocna 16 h przechodząca przez
  północ drukuje `N2`.
- **T47-04 — exact match:** ten sam czas trwania, lecz inny początek/koniec
  niż konfiguracja, nadal daje `WORK_CODE_MAPPING_REQUIRED`.
- **T47-05 — 14 h bez kodu:** nie powstaje kod „z sufitu”; wynik to
  `WORK_CODE_MAPPING_REQUIRED`.
- **T47-06 — zabezpieczenia:** TRAINEE i sprzeczne provenance zachowują
  dotychczasowe odmowy.
- **T47-07 — zwykły PDF:** mała obsada nadal daje jednostronicowy dokument z
  obecną tabelą i legendą.
- **T47-08 — 17 osób:** PDF ma więcej niż jedną stronę, wszystkie 17 nazw
  występuje dokładnie raz jako pracownik, a każda ma razem PLAN i WYK.
- **T47-09 — powtarzane nagłówki:** każda strona wielostronicowego PDF ma
  wymagane nagłówki, pełny miesiąc i numer strony.
- **T47-10 — czytelność:** render każdej strony do obrazu nie wykazuje
  uciętych wierszy, nachodzenia tabeli na legendę/stopkę ani tekstu poza
  stroną.
- **T47-11 — pion produkcyjny:** co najmniej jeden przypadek 4 h albo 16 h
  przechodzi przez rzeczywisty zapis obiektu/katalogu, PLAN, wybór kandydata
  i produkcyjny eksport; test nie wstawia ręcznie końcowego PDF ani nie mockuje
  `generate_schedule_pdf`.

Testy jednostkowe mogą zbudować minimalny stan dla samej paginacji i
mapowania, ale T47-11 ma potwierdzić prawdziwe połączenie warstw.

## 9. Weryfikacja proporcjonalna do zmiany

Implementator uruchamia:

- celowane T47-01…T47-11;
- istniejące testy `tests/test_t020.py` dotyczące mapowania, provenance,
  24 h i układu PDF;
- render stron testowego PDF do PNG i kontrolę wizualną;
- `ruff check` tylko dla zmienionych plików;
- `git diff --check`.

Pełna suita repozytorium jest opcjonalna i wymaga osobnej zgody OWNERA.

## 10. Proces i oczekiwany werdykt CC

To mały task naprawczy z dwoma logicznymi etapami:

1. istniejące kody 2/4/16 h;
2. podział istniejącego wydruku na strony.

Bez refaktoru pomiędzy etapami. CC przed implementacją sprawdza przede
wszystkim, czy zachowanie można osiągnąć w jednym istniejącym module i czy
macierz nie wymusza nowej logiki produktu. Jeżeli tak, architekt nie jest
potrzebny. Do architekta wracamy wyłącznie wtedy, gdy CC wykaże konkretną
sprzeczność ownership albo konieczność zmiany publicznego kontraktu.

Oczekiwany werdykt preimplementation:

- `PASS — READY_FOR_IMPLEMENTATION`, albo
- `FAIL` tylko z konkretnym `TRACE`, `OWNERSHIP` i reproduktorem sprzeczności.

Do PASS: CC READ-ONLY.

## 11. EXACT TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-T047/brief.md
- rota/application/schedule_export.py
- tests/test_t020.py
- tests/test_t047_print_export.py
