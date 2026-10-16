# ROTA-MANUAL-MIDDLE-ROLE-BLOCK — „Dodaj pracę” zapisuje świadome odstępstwo roli

STATUS: READY FOR INDEPENDENT PREIMPLEMENTATION CHECK; IMPLEMENTATION HOLD.
DATA: 2026-10-16.
BASE_SHA: e38a966df9f5e444025c87173a3eb284b090a2c3.
BRANCH: codex/rota-manual-middle-role-block.

## 1. Cel i PRODUCT_TRUTH

Osoba z obsady sklepu może na świadome polecenie koordynatora wykonać
dodatkową pracę w innej roli, nawet bez zapisanej autoryzacji zastępstwa.
„Dodaj pracę” zapisuje wtedy pracę, naruszenie ROLE-01/PREFERENCE i ślad
decyzji człowieka. Nie zmienia stanowiska ani dopuszczeń pracownika.

Źródła:
- OWNER 2026-10-16: „nasz program nigdy nie zabrania koordynatorowi wychodzić
  poza zasady. Zapisuje odchylenie koordynatora” — przywołane w przekazaniu
  ROTA-MANUAL-MIDDLE-ROLE-BLOCK; zadanie ma być wykonane przed refaktorem.
- OWNER_ACCEPTED z rozmowy o F1: „Tak, koordynator ma wszelkie prawa łamać
  zasady bo to jego odpowiedzialność, Rota sama zasad nie łamie zasady
  przestrzega a decyzje Koordynatora zapisuje w pamięci.”
- OWNER 2026-10-16, członkostwo: „jeśli ktoś nie jest przypisany do obiektu
  nie istnieje dla Rota. Zasada jest taka, że jak koordynator chce kogoś
  z innego sklepu najpierw dopisuje go do obsady.” Odmowa przy braku aktywnego
  członkostwa pozostaje; nie jest wyjątkiem roli ani blokadą tej decyzji.
- `tasks/ROTA-T065-MANUAL-MIDDLE-SHIFT/brief.md`: istniejąca akcja, kształt
  Assignment, zapis, saldo i eksport dodatkowej pracy; ten brief zastępuje
  wyłącznie dawną odmowę braku autoryzacji w §6 oraz oczekiwania MM-05
  i częściowej autoryzacji. MM-06 zachowuje sens.
- `tasks/ROTA-T065-CONFIGURABLE-ROLES/brief.md` §8: jeden owner pokrycia roli;
  `tasks/ROTA-UNMAPPED-DEVIATION-RULES/brief.md`: ROLE-01 → PREFERENCE,
  istniejąca polska etykieta i pion zapisu odstępstwa/decyzji.

Źródło techniczne: wiersz BOARD z propozycją CC, zgłoszenie `7756b05`,
doprecyzowanie członkostwa `e38a966`. Propozycja implementacyjna CC sama
w sobie nie jest decyzją produktową. Autor sprawdził punktowo nazwanych
ownerów na BASE_SHA; nie uruchamiał testów produktu ani runtime reproduktora.

## 2. Zachowanie użytkownika

Wyzwalacz: istniejące „Dodaj pracę” w ORDINARY; osoba ma aktywne członkostwo,
wskazana rola istnieje i jest aktywna w katalogu tego obiektu, a przedział
spełnia istniejące wymagania poprawnego zapisu pracy.

Przykład: kierownik należący do obsady dostaje dodatkową pracę 10:00–16:00
jako sprzedawca. Bez pełnej autoryzacji tej roli zapis przechodzi, ale
validator emituje ROLE-01. Dopuszczenie pokrywające tylko 10:00–13:00 nie
znosi naruszenia pracy 10:00–16:00. Autoryzacja aktywna i pokrywająca cały
przedział albo zgodne stanowisko oznacza brak ROLE-01.

Odczytywane dane: aktualne członkostwo i stanowisko, katalog ról obiektu,
aktualne RoleCoverageAuthorization, przedział i rola dodawanej pracy.
Zapis: istniejący potomny ScheduleVersion z realnym PRIMARY bez demandu,
`manual_work_role_id`/`manual_work_role_name`, Deviation gdy wykryto naruszenie,
dotychczasowy CoordinatorAction ze śladem ręcznej korekty. „Pamięć” to
istniejąca pamięć decyzji, bez nowej tabeli i bez dodatkowego typu akcji.

Stanowisko, autoryzacje, katalog, godziny docelowe i rodzic pozostają bez zmian.
Odstępstwo w jednej pracy nie tworzy trwałego uprawnienia do danej roli.
Nie uruchamia automatycznego REPLAN i nie rozluźnia reguł automatu.

UI po zapisie/odświeżeniu korzysta z obecnej listy odchyleń i bieżących
ostrzeżeń: „brak wymaganej roli”, osoba i data w istniejącym komunikacie.
Bez nowego modala, pola zgody, endpointu lub checkboxa przed zapisem.
Finalizacja i eksport zachowują istniejące zasady kategorii PREFERENCE.
Wyświetlanie godzin i historycznego stanowiska w eksporcie bez zmian;
nie dopisywać roli wykonywanej pracy do komórki wydruku.

Błędy: obiekt inny niż ORDINARY, nieznana/nieaktywna/obca rola i brak
aktywnego członkostwa nadal odrzucają zapis przed utworzeniem dziecka.
W ostatnim przypadku koordynator najpierw dopisuje osobę do obsady, potem
ponawia „Dodaj pracę”. Istniejące bramki integralności Assignment i atomowość
zapisu pozostają. Awaria zapisu nie zostawia częściowej wersji/akcji.
Zadanie nie znosi ochrony historycznych lub rozpoczętych służb.

## 3. Jeden owner i literalna zmiana

1. `rota/planning/eligibility.py`: wydzielić z obecnego `role_covers`
   funkcję `role_covers_interval(role_id, start, end, membership, authorizations)`.
   Dla konkretnej roli sprawdza dokładnie obecne warunki: zgodne stanowisko
   albo jedna aktywna autoryzacja tego pracownika i tej roli, pokrywająca
   cały przedział. Nie sumować częściowych autoryzacji, nie tworzyć hierarchii
   ról ani nowych reguł. Pula autoryzacji pozostaje z obecnego kontekstu obiektu.
   `role_covers(demand, ...)` zachowuje True przy braku required_role_id,
   a dla wymaganej roli deleguje do helpera. Bez zmiany wyniku istniejących
   konsumentów i bez ponownego sprawdzania członkostwa w tym helperze.

2. `rota/planning/validator_checks_availability.py::_check_role`: dodać
   ścieżkę dla pracy środkowej z manual_work_role_id i bez demandu. Użyć
   manual_work_role_id oraz realnego początku/końca Assignment i tego samego
   helpera. Niepokryta rola → ViolationDetail ROLE-01 z assignment_id tej
   pracy. Dla poprawnego członkostwa powstaje jedno naruszenie roli tej pracy.
   Nie przypisywać jej ról z nakładających się demandów i nie wyłączać
   `_covered_demands` dla innych, nietagowanych legacy Assignment.
   Istniejący check członkostwa pozostaje jego ownerem; nie dodawać kolejnego.

3. `rota/application/manual_middle_work.py`: usunąć wyłącznie odmowę braku
   autoryzacji roli i lokalny `_authorizes_manual_work_role`; jego jedyny
   konsument to usuwana bramka w tym samym pliku (sprawdzone wyszukaniem).
   Zachować kontrolę ORDINARY, aktywnej roli właściwego obiektu i aktywnego
   członkostwa. Dalej delegować do `apply_manual_correction` bez drugiego
   wywołania walidatora albo samodzielnego zapisu Deviation/CoordinatorAction.
   Uaktualnić opisy, które nazywają brak autoryzacji bezwzględną odmową.

Istniejące mapowanie ROLE-01/PREFERENCE i polska etykieta już są dostarczone
na BASE_SHA. Nie zmieniać ich ponownie. Praca środkowa pozostaje poza pokryciem
ShiftDemand: nowy check dotyczy roli samej pracy, nie COVERAGE-01.

## 4. Redukcja przed implementacją — jedno przejście

SOURCE: decyzja OWNERA o świadomych odstępstwach; NECESSITY: po zdjęciu bramki
potrzebna jest walidacja pracy bez demandu, aby zachować ślad naruszenia.
Minimalny adapter to helper przedziałowy wycięty z obecnego ownera i jego
użycie przez dwie obecne ścieżki. Usuwamy lokalną kopię sprawdzenia.
Nie są potrzebne nowe modele, persistence, walidator, workflow ani UI/API.
Nie jest to niezależny PASS autora własnemu kontraktowi.

## 5. Minimalny dowód po implementacji

Zachować pierwotny MM-05 jako reproduktor odmowy na BASE, a na exact SHA
poprawki zmienić jego oczekiwanie zgodnie z nową decyzją OWNERA:
- MM-05: rzeczywiste `add_manual_middle_work` bez autoryzacji zapisuje dziecko,
  ROLE-01/PREFERENCE i CoordinatorAction dotyczący tej pracy; stanowisko,
  autoryzacje i rodzic bez zmian. Odczyt miesiąca przez router prezentuje
  istniejącą polską etykietę/ostrzeżenie, bez komunikatu 400.
- MM-06: zgodne stanowisko oraz aktywna autoryzacja dokładnie pokrywająca
  pracę nie generują ROLE-01. Istniejące testy tego ownera zachowują sens.
- Zmieniony test częściowego pokrycia: zapis z ROLE-01 zamiast odmowy.
  Małe warianty tej samej klasy: za późny początek i za wczesny koniec;
  nieaktywna autoryzacja nie uprawnia. Bez kompletnej nowej macierzy ról.
- Regresja granicy: dodatkowa praca nakładająca się na demand innej roli
  nadal nie pokrywa demandu i nie dziedziczy jego roli. Własna rola manualna
  jest oceniana także przy braku jakiegokolwiek demandu.
- Zachować testy integralności i dodać brak/wyłączone członkostwo oraz
  nieaktywną/obcą rolę, jeżeli nie mają istniejącego dowodu. Odmowa pozostawia
  current/history/pamięć bez zmian. Nie rozbudowywać testów upstream gates.

Docelowy plik testowy: `tests/test_t065_manual_middle_shift.py`; poprawić
również jego nieaktualne opisy odmowy roli i braku jakiegokolwiek ROLE-01.
Nowy pion jest w istniejącym application → SQLite → validator → Deviation
→ pamięć → odczyt routera. Bez mocka samego helpera jako dowodu działania.
Użyć istniejących testów z `tests/test_t065_configurable_roles.py` dla
niezmienionej semantyki role_covers i automatu, bez kopiowania ich kontraktu.
Eksport/UI nie są zmieniane; wystarczy istniejący test MM-10 projekcji,
nie nowa pełna sesja przeglądarki.

Polecenia pytest z `.venv\Scripts\python.exe` (w worktree dopuszczalna
pełna ścieżka interpretera głównego repo), tylko te celowane testy i wymagany
mechaniczny gate. Bez pełnej regresji bez osobnej zgody OWNERA i konkretnego
ryzyka. Precheck briefu nie uruchamia testów produktu, reproduktorów ani pionu.
Po dostawie FAIL wymaga TRACE + OWNERSHIP + niezależnego REPRO na exact SHA.

## 6. Granice i zakres

OUT_OF_SCOPE: inne reguły/odstępstwa; osłabianie integralności danych;
brak członkostwa jako wyjątek; automatyczna praca środkowa; zapis trwałego
dopuszczenia z samej korekty; zmiana historii, solvera, UI/API/eksportu,
mapowania kategorii, nowe zgody lub pamięć; refaktor plików.
WORK_PERIOD-01, FULL_HOUR-01, SITE_RULE-01, ASSIGN są odłożone decyzją OWNERA
w ODLOZONE, nie otwierać ich ponownie przy tej korekcie.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: rota/planning/eligibility.py --symbol role_covers; rota/planning/validator_checks_availability.py --symbol _check_role; rota/application/manual_middle_work.py --symbol add_manual_middle_work; rota/application/manual_middle_work.py --symbol _authorizes_manual_work_role
- REASON: jeden owner roli, nowy adapter przedziałowy i usunięcie jego lokalnego duplikatu.

Po zamrożeniu zakresu uruchomić `python where.py <file>` dla trzech plików
i warianty `--symbol` dla powyższych symboli; po implementacji również dla
`role_covers_interval`. Przeczytać trafienia przed wnioskiem o ownerze.
Nie uruchamiać mapy w samym prechecku briefu.

TASK_SCOPE:
- tasks/ROTA-MANUAL-MIDDLE-ROLE-BLOCK/brief.md
- tasks/ROTA-MANUAL-MIDDLE-ROLE-BLOCK/repo_before.hash
- tasks/ROTA-MANUAL-MIDDLE-ROLE-BLOCK/round_01/
- rota/planning/eligibility.py
- rota/planning/validator_checks_availability.py
- rota/application/manual_middle_work.py
- tests/test_t065_manual_middle_shift.py

KONIEC TASK_SCOPE.

## 7. Przekazanie

Niezależny precheck Codexa: decyzje, jednoznaczność, testowalność,
minimalność i zachowanie jednego ownera. Potem ocena merytoryczna CC;
obie bramy przed implementacją. Autor nie wystawia własnemu briefowi
niezależnego PASS. Po dostawie audyt exact SHA i nowy raport
`round_01/tests/tests_r<n>.txt`, bez nadpisywania poprzednich. Merge tylko OWNER.
