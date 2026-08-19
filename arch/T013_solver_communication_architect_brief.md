# Handoff brief for architect: solver communicates real options to the coordinator (proponowane T013)

## Status

**GOTOWE DO PRZEKAZANIA ARCHITEKTOWI po spełnieniu zapisanego niżej
warunku wejściowego T012 + T016 — decyzje produktowe zamknięte 2026-08-16.**

Czysto faktograficzny brief, bez proponowanego rozwiązania. Nazwa "T013" to
robocza etykieta, nie zamrożony identyfikator.

## Skąd to zadanie

Właściciel (Paweł), po analizie realnego audytu T011-INTEGRATION
2026-08-15: program przy DECISION_REQUIRED ma zachowywać się jak "sfinks"
— ma realne możliwości (np. wsparcie zewnętrzne), ale koordynator musi już
znać architekturę systemu, żeby wiedzieć, o co zapytać. Właściciel chce
programu, który **komunikuje koordynatorowi co zrobić**, gdy solver
utknie — i zwrócił uwagę, że dzisiejsze komunikaty mogą być zbyt
"ejajowe" (żargon techniczny), niezrozumiałe dla zwykłego człowieka; ich
formę trzeba przemyśleć, ewentualnie uprościć.

To zadanie jest świadomie oddzielone od 24h zmiany (patrz
`T012_24h_shift_architect_brief.md`) — to zmiana sposobu raportowania
istniejących opcji, nie nowa reguła produktowa.

**Warunek wejściowy**: T013 powstaje po ukończeniu i zmergowaniu T012 oraz
T016 (`T016_emp02_active_period_architect_brief.md`). Dzięki temu projektuje
komunikację na docelowej semantyce 24h i nie musi tłumaczyć ani utrwalać
wycofywanego kodu `EMP-02`.

## Stan dzisiejszego kodu: cztery miejsca, gdzie solver się zatrzymuje

Wszystkie w `rota/planning/engine.py`, budują `DecisionRequiredPayload`
(`rota/planning/engine_types.py:30-34`: `blocking_shift_demands`,
`blockers`, `load_blocker`, `unblocking_options: list[str]`).

1. `_decision_for_unassignable` (linia 132-156) — brak jakiegokolwiek
   uprawnionego pracownika do demandu. `unblocking_options` (stała lista,
   zawsze identyczna, niezależna od kontekstu):
   `["potwierdzenie X/Y", "świadome ściągnięcie pracownika z wolnego",
   "świadome odwołanie/override urlopu zgodnie z kontraktem", "świadome
   wyłączenie DAY_ONLY"]`.
2. `_decision_for_conflict` (linia 176-206) — REST-01, kilka demandów
   niemożliwych do wspólnego pokrycia. `unblocking_options` zawsze:
   `["świadoma ręczna korekta zgodnie z kontraktem"]` — jeden, stały,
   ogólny tekst niezależnie od sytuacji.
3. `_decision_for_conflicts` (linia 295-334) — konflikt na już zapisanym
   (frozen) Assignment. `unblocking_options`: `["świadome odmrożenie
   Assignment i ponowne planowanie", "świadoma ręczna korekta frozen
   Assignment zgodnie z kontraktem"]`, plus opcjonalnie "świadoma
   akceptacja >Xh / 7 kolejnych dni" jeśli dotyczy też LOAD-01.
4. `_load_decision` (linia 386-415) — przekroczenie progu godzin w 7
   kolejnych dniach. `unblocking_options`: `["świadoma akceptacja >Xh / 7
   kolejnych dni"]`.

## Fakt (skorygowane): wsparcie zewnętrzne wspomniane w jednej z czterech list, żargonem

Sprawdzone bezpośrednio w kodzie. Trzy z czterech list (`_decision_for_conflict`,
`_decision_for_conflicts`, `_load_decision`) rzeczywiście nigdy nie wspominają
wsparcia zewnętrznego. Ale `_decision_for_unassignable` (punkt 1 powyżej)
zawiera pozycję `"potwierdzenie X/Y"` — to jest realne odwołanie do
mechanizmu wsparcia zewnętrznego (`"X/Y"` to termin ze spec —
`grep "X/Y" arch/spec.md`, dot. `ExternalSupportWindow`/WINDOW-02/03), ale
zapisane żargonem niezrozumiałym bez znajomości wewnętrznej terminologii
spec. Mechanizm wsparcia zewnętrznego istnieje i działa
(`rota/planning/eligibility.py:204-209`, `rota/planning/validator.py:420-428`,
`SiteProfile.external_support_enabled`, `SiteMembership(kind=EXTERNAL_SUPPORT)`,
`ExternalSupportWindow`) — solver go **użyje**, jeśli dane wejściowe je
dają, ale nawet ta jedna wzmianka nie tłumaczy koordynatorowi, co właściwie
ma zrobić. W pozostałych trzech listach wsparcie zewnętrzne nie pojawia się
wcale, nawet w tej formie. Te cztery listy są statyczne, przypisane do typu
reguły, nie liczone dynamicznie względem tego, co faktycznie mogłoby
zmienić wynik.

## Fakt: `Blocker.condition` to surowy kod reguły, nie zdanie po ludzku

`rota/planning/engine_types.py:17-20`:
```python
@dataclass
class Blocker:
    employee_id: str
    condition: str
```
`condition` przyjmuje dziś wartości takie jak `"REST-01"`, `"DAY_ONLY-01"`,
`"SICK_LEAVE-01"`, `"LEAVE_GRANTED-01"`, albo (dla SiteRule) dokładny
`rule_version_id` — wewnętrzny identyfikator reguły, nie zdanie
wyjaśniające sytuację. Przykład z realnego artefaktu audytu
(`artifacts/t011_pipeline/coordinator_wall_retry_after.json`):
```json
"blockers": [
  {"employee_id": "ANNA", "condition": "REST-01"},
  {"employee_id": "BARTEK", "condition": "REST-01"},
  {"employee_id": "FILIP", "condition": "REST-01"}
]
```
Koordynator widzi kod `"REST-01"` bez tłumaczenia, co to znaczy po ludzku
("między dwiema zmianami tego pracownika nie ma wystarczającej przerwy na
odpoczynek").

## Frozen Product Contract dziś nic nie mówi o formacie komunikatu

`arch/spec.md` definiuje typy `DECISION_REQUIRED`/`Blocker`/
`unblocking_options` strukturalnie (jakie pola istnieją), ale nie określa
wymagań co do języka/zrozumiałości treści tych pól dla człowieka
nietechnicznego. To realny brak w kontrakcie, nie coś do wywnioskowania.

## DECYZJE WŁAŚCICIELA (2026-08-15/16, rozstrzygnięte)

1. **Dynamiczność**: `unblocking_options` mają przestać być statyczną listą
   per typ reguły. Program ma proponować **tylko to, co realnie pomogłoby**
   w danej, konkretnej sytuacji — albo wprost poinformować koordynatora,
   że przy żadnym dostępnym układzie nie da się automatycznie przygotować
   grafiku. To rozstrzyga wcześniejsze pytanie o statyczność na "nie,
   ma b{� liczone dynamicznie względem konkretnego blockera".
   **Doprecyzowanie właściciela 2026-08-16**: koordynatora interesuje
   kompletny, poprawny grafik, nie droga solvera do wyniku. Solver może
   wykonywać wewnętrznie kolejne próby, symulacje i ponowne PLAN, ale nie
   pokazuje etapów pośrednich jako rozwiązań. Na zewnątrz zwraca kompletny
   poprawny grafik albo końcowe `DECISION_REQUIRED` z konkretną decyzją
   koordynatora, np. dodaniem nazwanego pracownika wsparcia zewnętrznego do
   bieżącej obsady lub świadomym ręcznym naruszem HARD zgodnie z
   istniejącym kontraktem Deviation/finalize.
2. **Zakres**: wszystkie 4 miejsca (`_decision_for_unassignable`,
   `_decision_for_conflict`, `_decision_for_conflicts`, `_load_decision`)
   naraz, nie pilotaż na jednym.
3. **Odbiorca**: wyłącznie koordynator obiektu lub jego zmiennik. Bez
   osobnej warstwy technicznej/administracyjnej.
4. **Logowanie/uprawnienia**: żadnych nowych mechanizmów logowania ani
   nadawania uprawnień w ramach tego zadania, chyba że pojawi się wyraźne
   wymaganie w przyszłości.
5. **Ludzkie zamienniki kodów — ustalone przez właściciela (2026-08-16)**:

   | Kod | Tekst dla koordynatora |
   |---|---|
   | `UNAVAILABLE-01` | "Koliduje z checkbox: Ogólna dostępność" |
   | `DAY_ONLY-01` | "Koliduje z checkbox: Nocka" |
   | `SICK_LEAVE-01` | "Koliduje z zapisem: Chorobowe" |
   | `LEAVE_GRANTED-01` | "Koliduje z zapisem: Urlop" |
   | `REST-01` | "Koliduje z odpoczynkiem dobowym" |
   | `LOAD-01` | "Koliduje z tygodniowym czasem pracy" |
   | `EXTERNAL-01` | "Wsparcie zewnętrzne" |
   | `EXTERNAL_SUPPORT_DISABLED` | "Wsparcie zewnętrzne" |
   | `MEMBERSHIP_DISABLED` | **Niewidoczny dla koordynatora** — kandydat odrzucony z tego powodu jest pomijany przy budowaniu komunikatu, choć kod może pozostać używany wewnętrznie. |
   | `EMP-02` | **Nie dotyczy** — mechanizm wycofywany całkowicie, patrz `T016_emp02_active_period_architect_brief.md`. Kod nie będzie już występował po T016. |
   | `DAY_SHIFT_OFF-01` | **Odłożone.** Właściciel (2026-08-16): brak dziś ustalonej definicji/nazwy w Panelu Sterowania, a decyzja, czy ta reguła jest w ogóle potrzebna, jest otwarta. Nie blokuje reszty T013 — architekt zostawia ten kod bez tłumaczenia do czasu osobnej decyzji. |
   | `EXTERNAL-01`/`EXTERNAL_SUPPORT_DISABLED`, kontekst dodatkowy | Właściciel (2026-08-16): sam mechanizm rejestracji z wyprzedzeniem (`ExternalSupportWindow`) jest dziś praktycznie martwy — nikt nie ustala stałego wsparcia zewnętrznego z góry. Zostaje jako opcja dla koordynatora ("może jej użyć"), więc tekst ma go o niej poinformować, ale nie trzeba tego dalej rozbudowywać. |
   | dowolny `rule_version_id` z SiteRule | Koordynator widzi **opis zapisanej reguły**, nie techniczny `rule_version_id`. Sposób pobrania i reprezentacji opisu pozostaje decyzją techniczną architekta. |

   `MEMBERSHIP-01` (istniejący, ogólny kod obok `MEMBERSHIP_DISABLED`) jest
   traktowany tak samo: kandydat odrzucony z tego powodu nie pojawia się na
   liście pokazywanej koordynatorowi. Tylko koordynator decyduje, kto należy
   do obsady; program nie proponuje mu automatycznego dodawania konkretnego
   odrzuconego kandydata. Oba kody mogą nadal istnieć i być sprawdzane
   wewnętrznie.
6. **Spójność ze słownictwem Panelu Sterowania (2026-08-16)**: tam, gdzie
   `arch/OWNER_DECISION_T010_PANEL_STEROWANIA_2026-08-13.md` już ustalił
   nazwę pola/checkboxa widocznego dla koordynatora, ludzki zamiennik kodu
   MUSI używać tej samej nazwy, nie nowego sformułowania wymyślonego
   niezależnie — inaczej koordynator dostaje dwa różne słowa na to samo
   zjawisko (raz w Panelu przy konfiguracji, raz w komunikacie o blokadzie).
   Znane dziś powiązania:
   - `UNAVAILABLE-01` → **"Ogólna dostępność"** (§5 tego dokumentu, checkbox
     w matrycy dostępności pracownika).
   - `DAY_ONLY-01` → **"Nocka"** (§6, pole `day_only`).
   - `SICK_LEAVE-01` → **"choroba"**, `LEAVE_GRANTED-01` → **"urlop"** (§7).
   Dla kodów bez odpowiednika w tym dokumencie (LOAD-01, EXTERNAL-01,
   EXTERNAL_SUPPORT_DISABLED) właściciel ustalił nazwę od zera — patrz
   tabela w punksie 5, gdzie jest już rozstrzygnięte.

   **To samo dotyczy nowych checkboxów, które dopiero wprowadza T012**
   (`T012_24h_shift_architect_brief.md`) — tes zamknęte nazwy muszą trzymać:
   - checkbox **"24"** (poziom pracownika, SOFT) — jeśli komunikat solvera
     ma kiedykolwiek odnosić się do tej kwalifikacji (np. tłumaczt�c, że
     grafiku nie dało się ułożyć nawet po sięgnięciu po pracowników z tym
     checkboxem), ma używać dokładnie nazwy **"24"**, nie innego określenia.
   - katalog obiektu **24h / 12h / INNY** (poziom obiektu, SiteProfile) —
     jeśli komunikat odnosi się do tego, jaki typ zmiany obowiązuje dany
     dzień, ma używać tych samych trzech nazw.
   REST-01 pozostaje bez ustalonej nazwy checkboxa mimo T012 — wymagany
   odpoczynek to wartość liczbowa przypisana do pozycji katalogu, nie
   osobny checkbox; właściciel i tak proponuje dla niego tekst od zera per
   punkt 5.

## Otwarte pytania techniczne pozostawione architektowi

- Czy tłumaczenie kodu reguły na zdanie po ludzku ma być osobną warstwą
  (np. słownik `RULE_CODE -> szablon zdania` w warstwie aplikacyjnej/UI),
  czy `unblocking_options`/`condition` mają zostać zmienione u źródła w
  `rota/planning/engine.py`? Pierwsze nie uszerza zamrożonego kontraktu
  planningu; drugie tak.
- Mechanika "dynamicznego liczenia" opcji: czy silnik ma faktycznie
  próbować symulować, co by się stało połączeniu wsparcia
  zewnętrznego/zmianie danej reguły (i dopiero wtedy proponować tę opcję),
  czy wystarczy prostsza heurystyka per typ bloku? To rozstrzygnięcie
  czysto techniczne, zostawione architektowi.

Decyzje produktowe właściciela są zamknięte. Dokument nie proponuje
architektury tłumaczenia ani techniki dynamicznego sprawdzania opcji — te
wybory pozostają architektowi w granicach decyzji zapisanych powyżej.
