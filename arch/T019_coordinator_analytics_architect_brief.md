# Handoff brief dla architekta — ROTA-T019 Analityka koordynatora

STATUS: OWNER INTENT CLOSED — READY FOR ARCHITECT CONTRACT

DATE: 2026-08-20

TASK_ID: ROTA-T019

BASE_BRANCH: main

BASE_SHA: 9618477f6014fad63699a154b04730e2b8ff1db2

DEPENDS_ON: T011-D + T014 + T016 + T017 + T018 merged on main

FOLLOWED_BY:

- T020 — wydruk/eksport grafiku;
- T021 — właściwy interfejs użytkownika.

## 1. Intencja właściciela

W przyszłym UI koordynator ma mieć wejście „Analityka”, pokazujące informacje,
które Rota już oblicza i wykorzystuje przy planowaniu oraz bilansie godzin.

To zadanie nie ma tworzyć nowego subsystemu analitycznego. Ma udostępnić
koordynatorowi istniejącą prawdę operacyjną w jednym, jednoznacznym read modelu.

Właściciel nie zamawia:

- nowych wskaźników zarządczych;
- prognoz;
- statystyki wydajności pracowników;
- payrollu;
- formalnej kwalifikacji godzin jako nadgodzin;
- ewidencji kadrowej;
- wykresów wymagających nowych agregacji;
- UI w T019;
- wydruku w T019.

## 2. Istniejąca powierzchnia — fakty na BASE_SHA

### 2.1 WorkBalance

`rota/domain.py::WorkBalance` już zawiera:

- `employee_id`;
- `month`;
- `target_hours`;
- `planned_hours`;
- `realized_hours`;
- `month_balance`;
- `unresolved_carryover`;
- `quarter_balance`.

`target_hours` jest wejściem koordynatora. Pozostałe pola bilansu są
rekonstruowane z bieżących danych operacyjnych; nie są drugim, ręcznie
edytowalnym źródłem prawdy.

### 2.2 Odczyt miesiąca

`rota.application.open_month.open_month(conn, *, site_id, month)` zwraca
`OpenMonthView`, w tym:

- pracowników i membership wybranego Site;
- bieżącą wersję oraz historię wersji miesiąca;
- aktualne availability;
- `work_balances`;
- warnings.

`OpenMonthView.work_balances` zawiera bilans miesiąca z rzeczywistym carry-in
wcześniejszych miesięcy kwartału, o ile dane wejściowe na to pozwalają.

### 2.3 Jawny odczyt kwartału

`rota.application.balance_read.quarter_balance(
conn, *, employee_id, quarter_first_month
)` zwraca:

`tuple[list[WorkBalance], list[str]]`.

Jeżeli któregokolwiek miesiąca kwartału brakuje `target_hours`, funkcja nie
zwraca częściowego bilansu i nie zgaduje normy. Zwraca pustą listę oraz warning
wskazujący brakujący miesiąc.

### 2.4 Źródła obliczeń

`rota.persistence.work_balance_repository` rekonstruuje bilans z:

- zapisanych `target_hours`;
- Assignment z wyłącznie bieżących ScheduleVersion;
- AvailabilityRecord;
- CalendarDay;
- istniejącej semantyki `rota.balance`.

Historyczne/niebieżące wersje grafiku nie mogą zwiększać aktualnych godzin.
NN/CANCELLED nie mogą być liczone jako praca. PLAN i REALIZED pozostają
odrębnymi wartościami.

### 2.5 Semantyka wielu Site

`WorkBalance` nie ma `site_id`. Employee nie jest własnością jednego Site.
Godziny pracownika są rekonstruowane z jego bieżących Assignment ze wszystkich
Site.

Dlatego ekran otwarty z kontekstu Site może użyć obsady tego Site do wybrania
pracowników, ale pokazywane godziny i saldo pracownika są globalne — łącznie ze
wszystkich obiektów. UI musi to później nazwać wprost. Nie wolno przedstawiać
tych wartości jako godzin wyłącznie na aktualnie otwartym obiekcie.

## 3. Zamrożony zakres produktu T019

T019 ma dostarczyć jeden read-only application-level odczyt przygotowany dla
przyszłego ekranu „Analityka”.

Dla wybranego:

- `site_id`;
- miesiąca;
- wynikającego z niego kwartału;

odczyt ma umożliwić pokazanie dla każdego aktywnego członka obsady Site:

1. identyfikatora i nazwy pracownika;
2. miesiąca;
3. normy `target_hours`;
4. `planned_hours`;
5. `realized_hours`;
6. `month_balance`;
7. `quarter_balance` / narastającego salda;
8. `unresolved_carryover` w jego obecnej semantyce;
9. stanu dostępności danych oraz warningów o brakującej normie/kalendarzu;
10. jasnej informacji, że liczby godzin są łączne dla pracownika ze wszystkich
    Site.

Read model może zawierać trzy miesięczne pozycje kwartału albo równoważną,
jednoznaczną strukturę. Architekt wybiera minimalny kształt bez tworzenia
ogólnego frameworka raportowego.

## 4. Wyjaśnialność salda po nieobecności

Po T018 `SICK_LEAVE` i `LEAVE_GRANTED` zmniejszają efektywną normę WorkBalance
wyłącznie o kwalifikujące się dni robocze, według istniejącego kalendarza.

Samo pokazanie:

`target_hours`, `planned_hours`, `realized_hours`, `month_balance`

może być rachunkowo nieczytelne, ponieważ `month_balance` jest liczony względem
efektywnej normy po istniejącym adjustment, a `WorkBalance.target_hours`
pozostaje pierwotną normą koordynatora.

T019 nie tworzy nowej reguły. Read model powinien jednak ujawnić dokładnie
wartość już wykorzystaną w istniejącym obliczeniu — jako minimalne pole
wyjaśniające, np. `effective_target_hours` albo `excused_absence_hours`.

Warunki:

- użyć tej samej funkcji/tego samego wyniku co `rota.balance`;
- nie implementować równoległego filtrowania weekendów i świąt;
- nie zapisywać wartości pochodnej w bazie;
- brak kompletnego CalendarDay ma zachować istniejące fail-closed zachowanie;
- nazwa pola nie może sugerować świadczenia, wynagrodzenia ani rozliczenia ZUS.

Wybór minimalnego technicznego pola należy do architekta. Semantyka obliczenia
nie jest otwarta.

## 5. Stany prezentacyjne wymagane od read modelu

Read model musi rozróżnić co najmniej:

1. `AVAILABLE` — kompletne dane i policzony miesiąc/kwartał;
2. `MONTH_AVAILABLE_QUARTER_UNAVAILABLE` — miesiąc można pokazać, lecz jawny
   odczyt całego kwartału jest niedostępny przez brak normy w innym miesiącu;
3. `UNAVAILABLE` — brak danych wymaganych również do żądanego miesiąca;
4. warnings — literalne, deterministyczne komunikaty wskazujące pracownika i
   brakujący miesiąc/dane.

Nazwy enum/statusów są wyborem architekta; rozróżnienie semantyczne nie może
zniknąć. Brak danych nigdy nie oznacza zera.

## 6. Granice

T019 jest wyłącznie odczytem.

Nie wolno:

- zapisywać bilansu jako nowej tabeli lub cache będący drugim źródłem prawdy;
- zmieniać `target_hours` z ekranu analityki;
- modyfikować ScheduleVersion, Assignment, AvailabilityRecord lub CalendarDay;
- liczyć historycznych wersji grafiku;
- automatycznie kwalifikować dodatniego salda jako nadgodziny;
- tworzyć rozliczeń płacowych, dodatków nocnych albo absencyjnych;
- tworzyć site-local WorkBalance przez odjęcie pracy na innych Site;
- zmieniać solver, jego objective albo wyniki PLAN/REPLAN;
- dodawać wykresów, eksportu Excel/PDF lub wydruku;
- implementować UI.

T020 odpowiada za wydruk. T021 odpowiada za UI.

## 7. Oczekiwany kierunek techniczny — do zamrożenia przez architekta

Architekt ma określić najmniejszy application read model, który:

- korzysta z istniejących repozytoriów/odczytów zamiast powielać SQL;
- może być wywołany przez T021 bez importu `rota.persistence` w UI;
- zwraca wszystkie wiersze obsady jednym spójnym wynikiem;
- nie wykonuje częściowych zapisów ani ukrytych migracji;
- ma deterministyczną kolejność pracowników i miesięcy;
- nie wprowadza ogólnego query bus, dashboard framework ani report engine;
- zachowuje istniejące `open_month()` i `quarter_balance()` albo deleguje do
  ich właścicieli bez zmiany publicznej semantyki.

Architekt ma sprawdzić, czy wystarczy jeden nowy moduł w rodzaju
`rota/application/analytics_read.py`, czy bezpieczniejsze jest kompatybilne
rozszerzenie istniejącego `balance_read.py`. To jest wybór techniczny, nie nowa
decyzja produktowa.

## 8. Minimalna macierz dowodowa kontraktu

Kontrakt architekta powinien wymagać co najmniej:

1. jeden pracownik, kompletny miesiąc — wszystkie istniejące pola WorkBalance;
2. trzy miesiące kwartału — poprawne saldo narastające;
3. planned i realized pokazane oddzielnie, bez podwójnego liczenia;
4. NN/CANCELLED nie zwiększa godzin;
5. historyczna niebieżąca ScheduleVersion nie zwiększa godzin;
6. restore/select zmienia odczyt zgodnie z nowym current pointer;
7. restart bazy zwraca identyczny read model;
8. brak `target_hours` w miesiącu żądanym — brak zera i jawny unavailable;
9. brak normy w innym miesiącu kwartału — miesiąc nadal dostępny, kwartał
   niedostępny z warningiem;
10. SICK_LEAVE/LEAVE_GRANTED obejmujące weekend — adjustment wyłącznie za dni
    robocze i zgodność z T018;
11. wspólny pracownik na dwóch Site — jedna globalna suma godzin, bez
    duplikacji, z jawną etykietą cross-Site;
12. dwóch różnych pracowników/roster filter — brak wycieku wiersza osoby
    nienależącej do obsady otwartego Site;
13. read jest bez zapisu — snapshot tabel przed/po identyczny;
14. brak formalnego pola/komunikatu „nadgodziny” lub wyliczenia wynagrodzenia;
15. `open_month()` i `quarter_balance()` dotychczasowe regresje pozostają
    zielone.

## 9. Pytania dla architekta — wyłącznie techniczne

1. Minimalny DTO/read-model shape i miejsce modułu.
2. Jak bez powielenia obliczenia ujawnić adjustment efektywnej normy.
3. Jak złożyć miesięczny odczyt tolerujący brak wcześniejszej normy z pełnym,
   fail-closed odczytem kwartału.
4. Jak wykonać odczyt całej obsady bez N+1 SQL i bez nowego cache/persistence.
5. Literalny TASK_SCOPE i lista istniejących testów wymagających wyłącznie
   mechanicznej adaptacji.

Żadne z tych pytań nie otwiera nowych wskaźników ani zmiany WorkBalance.

## 10. Wymagany wynik pracy architekta

Architekt przygotowuje zamrożony kontrakt:

`tasks/ROTA-T019/brief.md`

z exact BASE_SHA, literalnym TASK_SCOPE, limitem nowych plików, kompletną
macierzą testów oraz bramkami:

1. Codex preimplementation audit;
2. dopiero po PASS — implementacja CC;
3. backend.py + pełna suita;
4. Codex implementation audit;
5. finalny gate architekta przed merge.

## 11. Relacja do T020 i T021

- T019 nie projektuje arkusza ani wydruku.
- T020 ma osobny obowiązkowy Checkpoint A: właściciel akceptuje szablon `.xlsx`
  przed implementacją generatora.
- T021 konsumuje read model T019 i operacje już istniejące; nie przenosi SQL ani
  obliczeń WorkBalance do warstwy UI.
