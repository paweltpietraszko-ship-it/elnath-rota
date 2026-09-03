# ROTA-T048 — usunięcie pięciu potwierdzonych anglicyzmów/nieczytelnych ID z UI

STATUS: PROPOZYCJA DO WERYFIKACJI CC — ZERO KODU PRODUKTU — IMPLEMENTACJA
DOPIERO PO PASS PREIMPLEMENTATION AUDIT

BASE_MAIN_SHA: `6a61e9aa9e67cc4fd9755ce66a751dce5b90c7e6`

Źródło: ręczny audyt kodu na prośbę OWNERA (2026-09-03), po tym jak Paweł
zgłosił żywy przykład (`missing target_hours for employee ..., quarter
carry-in reset to 0`) oraz surowe identyfikatory w UI (`Wersja: SV-...`,
`DEV-COORD-1`). Pełna lista znalezisk: backlog item 10 w pamięci CC
(`project_small_findings_backlog_2026-08-31.md`). OWNER zatwierdził
konkretne brzmienie każdej poprawki poniżej przed napisaniem tego briefu.

## 1. Cel

Naprawić pięć potwierdzonych, konkretnie zlokalizowanych anglicyzmów/
nieczytelnych identyfikatorów pokazywanych wprost koordynatorowi. Wyłącznie
zamiana tekstu/etykiet na już zatwierdzone przez OWNERA brzmienie polskie —
zero nowej logiki, zero nowych ekranów, zero zmiany zachowania solvera.

Jawnie POZA zakresem (OWNER_CORRECTED, 2026-09-03): zamiana `coordinator_id`
na czytelne imię/nazwisko (`History.tsx` kolumna „Koordynator”, `Decisions.tsx`
„Zgłoszono przez”) — pokrywa się z niezaprojektowanym jeszcze prawdziwym
logowaniem (ROTA-T024/T025, F1). Nie budować żadnego mechanizmu
rozpoznawania koordynatorów w tym Tasku.

## 2. Ostrzeżenie o zerowaniu przeniesienia kwartalnego (`assembler.py`)

`rota/application/assembler.py:130-133` (`_carry_in_before`) zwraca
całkowicie angielski tekst:

```
f"missing target_hours for employee {employee_id!r}, month {current.isoformat()}: "
"quarter carry-in reset to 0"
```

Ten sam plik ma 24 linie niżej (154-158) niemal bliźniaczy warning o braku
`target_hours`, już poprawnie po polsku — wygląda na przeoczenie jednego z
dwóch analogicznych warningów przy T041. Oba trafiają do tej samej listy
`warnings`, którą `MonthlyPlanning.tsx` pokazuje w banerze „Uwaga”.

### Wymagane zachowanie

Zamienić dokładnie na (wzorowane na sąsiednim, już zaakceptowanym tekście):

```python
f"Brak wpisanego miesięcznego limitu godzin (target_hours) dla "
f"pracownika {employee_id!r} w miesiącu {current.isoformat()} — "
"nadgodziny narastające z tego kwartału zostały wyzerowane, bo bez "
"tego limitu nie da się ich policzyć."
```

Zero zmian logiki — tylko treść stringa. `frontend/src/screens/MonthlyPlanning.tsx`
(`resolveWarningText`, linia 227) już podmienia `'employee_id'` na imię i
nazwisko z rosteru — nie dotykać tego mechanizmu, tekst przechodzi przez
niego bez zmian.

## 3. `DAY_SHIFT_OFF-01` i słowo „checkbox” (`decision_guidance.py`)

`rota/planning/decision_guidance.py::_render_condition` (linia 62-73):

- linia 65-66: `if raw_condition == "DAY_SHIFT_OFF-01": return raw_condition`
  — jedyny warunek DECISION_REQUIRED bez polskiego tekstu w całym pliku;
  zwraca surowy kod prosto na ekran „Decyzje koordynatora”
  (`Decisions.tsx:71`). Już raz zgłoszone i nienaprawione (audyt Cursora
  2026-08-22, `V-B8`, `tasks/ROTA-T021/brief.md:561`).
- `_BUILT_IN_CONDITION_TEXT` (linia 23-34) zawiera dosłowne angielskie
  słowo „checkbox” w trzech wpisach — ten sam wcześniejszy audyt to
  zgłosił, też nienaprawione.

### Wymagane zachowanie

W `_BUILT_IN_CONDITION_TEXT`:

```python
"UNAVAILABLE-01": "Koliduje z ustawieniem: Ogólna dostępność",
"DAY_ONLY-01": "Koliduje z ustawieniem: Nocka",
"SHIFT-24-01": "Koliduje z ustawieniem: 24",
"DAY_SHIFT_OFF-01": "Koliduje z zapisem: Wolne w dzień",
```

(pierwsze trzy zastępują istniejące wpisy z „checkbox”; czwarty jest nowy —
wzorowany na sąsiednich `SICK_LEAVE-01`/`LEAVE_GRANTED-01`, dopasowany do
`EmployeeDetail.tsx`'s istniejącej etykiety `DAY_SHIFT_OFF: "Wolne w dzień"`).

Usunąć specjalny warunek na liniach 65-66 — po dodaniu wpisu do
`_BUILT_IN_CONDITION_TEXT`, `DAY_SHIFT_OFF-01` trafia do zwykłej ścieżki
`if raw_condition in _BUILT_IN_CONDITION_TEXT` kilka linii niżej, bez
potrzeby osobnego warunku.

Nie dodawać wpisu do `_ACTION_TEMPLATES` dla `DAY_SHIFT_OFF-01` — brak
sugerowanej akcji dla tego blokera to osobny, głębszy brak funkcjonalny
(inny niż tłumaczenie tekstu), poza zakresem tego Tasku.

## 4. Surowa wersja grafiku i status (`MonthlyPlanning.tsx`)

`frontend/src/screens/MonthlyPlanning.tsx:620`:

```tsx
Wersja: {view.current_version.version_id} — status: {view.current_version.status}
{view.current_version.effective_from ? ` — obowiązuje od ${view.current_version.effective_from}` : ""}
```

oraz `:763-766` (panel „Historia wersji”):

```tsx
<span>{v.version_id}</span>
<span className="badge-pill badge-on">{v.status}</span>
```

`version_id` to techniczny hash (np. `SV-59bcb3c9b7154cc0b854de81b0737431`)
bez żadnej wartości informacyjnej dla koordynatora. `status` to surowa
wartość enuma `ScheduleStatus` (`WORKING`, `WORKING_WITH_DEVIATIONS`,
`FINAL_NO_DEVIATIONS`, `FINAL_WITH_DEVIATIONS`) — `History.tsx` ma gotową
mapę etykiet dla akcji (`ACTION_KIND_LABEL`), tu nic takiego nie istnieje.

### Wymagane zachowanie

Dodać w `MonthlyPlanning.tsx` mapę:

```tsx
const SCHEDULE_STATUS_LABEL: Record<ScheduleVersionOut["status"], string> = {
  WORKING: "Wersja robocza",
  WORKING_WITH_DEVIATIONS: "Wersja robocza (z odstępstwami)",
  FINAL_NO_DEVIATIONS: "Zatwierdzona",
  FINAL_WITH_DEVIATIONS: "Zatwierdzona (z odstępstwami)",
};
```

Linia 620 →
```tsx
Status: {SCHEDULE_STATUS_LABEL[view.current_version.status]}
{view.current_version.effective_from ? ` — obowiązuje od ${view.current_version.effective_from}` : ""}
```
(bez `version_id` — usunąć go z widoku całkowicie, nie zastępować niczym).

Linie 764-766 (`<span>{v.version_id}</span>` + status badge) → usunąć
`<span>{v.version_id}</span>`, zamienić badge na
`{SCHEDULE_STATUS_LABEL[v.status]}`. `key={v.version_id}` w linii 763
zostaje bez zmian — to identyfikator Reacta, niewidoczny dla koordynatora,
nie dotyczy tego Tasku.

Uwaga: `v.status !== "FINAL_NO_DEVIATIONS"` (linia 778) i inne porównania
surowej wartości enuma w logice (nie w tekście widocznym dla użytkownika)
zostają bez zmian — dotyczą tylko treści wyświetlanej wprost.

## 5. Surowe `demand_id`/`employee_id` na ekranie „Decyzje koordynatora” (`Decisions.tsx`)

`frontend/src/screens/Decisions.tsx`:

- linia 59-60: `{d.demand_id}: {formatDateTime(d.start_datetime)} – {formatDateTime(d.end_datetime)}`
  — surowy `demand_id` przed już czytelnym zakresem dat.
- linia 71: `{b.employee_id}: {b.condition}` — surowy `employee_id`.
- linia 81: `{detail.load_blocker.employee_id}: {detail.load_blocker.hours}h w tygodniu ...`
  — surowy `employee_id`.

### Wymagane zachowanie

- Usunąć `{d.demand_id}:` z linii 60 — sam zakres dat (`formatDateTime(d.start_datetime)
  – formatDateTime(d.end_datetime)`) już jednoznacznie identyfikuje blokującą
  zmianę, `demand_id` nie dodaje nic czytelnego. `key={d.demand_id}` w linii
  59 zostaje bez zmian (identyfikator Reacta).
- Dodać pobranie rosteru identycznie jak `MonthlyPlanning.tsx:220`
  (`api.listRoster(siteId).then(setRosterEmployees).catch(() => undefined)`
  w `useEffect` zależnym od `siteId`) i funkcję pomocniczą:
  ```tsx
  const nameFor = (employeeId: string): string =>
    rosterEmployees.find((r) => r.employee_id === employeeId)?.display_name ?? employeeId;
  ```
  (fail-safe: nieznane id nadal pokazuje surowy string zamiast pustki lub
  wyjątku — ten sam wzorzec co `History.tsx`'s `STATE_KEY_LABEL[key] ?? key`).
- Linia 71 → `{nameFor(b.employee_id)}: {b.condition}`.
- Linia 81 → `{nameFor(detail.load_blocker.employee_id)}: {detail.load_blocker.hours}h w tygodniu ...`.

`detail.requested_by` (linia 52, `coordinator_id`) NIE jest dotykane — poza
zakresem, patrz sekcja 1.

## 6. Nieprzetłumaczona wartość enuma w widoku „Przed/Po” (`History.tsx`)

`frontend/src/screens/History.tsx`'s `STATE_KEY_LABEL`/`stateKeyLabel`
tłumaczy klucze słownika w widoku różnicy stanu, ale `renderStateValue`
(linia 85-109) nigdy nie tłumaczy *wartości* — np. zapisane
`"planning_regime": "ORDINARY"` (`rota/application/bootstrap.py:140`,
`rota/application/durable_inputs.py:572,574`) pokaże się dosłownie jako
`ORDINARY`, mimo że klucz obok niego już jest po polsku
(„reżim planowania”). `"OCHRONA"` to już słowo polskie, nie wymaga wpisu.

### Wymagane zachowanie

Dodać obok istniejącego `STATE_KEY_LABEL` nową, równie prostą mapę tylko
dla tego jednego, potwierdzonego przypadku:

```tsx
const STATE_VALUE_LABEL: Record<string, string> = {
  ORDINARY: "standardowy",
};

function stateValueLabel(value: unknown): unknown {
  return typeof value === "string" && value in STATE_VALUE_LABEL ? STATE_VALUE_LABEL[value] : value;
}
```

W `renderStateValue`, w gałęzi `typeof value !== "object"` (ostatni
`return String(value)`), zastąpić na `return String(stateValueLabel(value))`.

Task NIE wymaga wyszukania i przetłumaczenia każdej możliwej wartości
enuma, jaka może się pojawić w tym widoku (`membership_kind`,
`readiness_state`, `kind` itp.) — to byłoby nowe, nieograniczone zadanie
bez zatwierdzonego przez OWNERA słownika. Ten Task naprawia jeden
potwierdzony, zgłoszony przypadek i zostawia mechanizm łatwy do
rozszerzenia (dokładnie ten sam wzorzec co `STATE_KEY_LABEL`), gdy
kolejne wartości zostaną zauważone i zatwierdzone.

## 6a. Istniejące testy, które ten Task musi zaktualizować (nie tylko dodać nowe)

Sprawdzone na `BASE_MAIN_SHA` (`git grep`), dokładnie te testy sprawdzają
dziś stare, angielskie/„checkbox” brzmienie i przestaną przechodzić po
sekcji 3 bez aktualizacji oczekiwanej treści:

- `tests/test_t013.py:98-106` (definicja oczekiwanej mapy tekstów),
  `:138-139` (**dziś explicite oczekuje, że `DAY_SHIFT_OFF-01` zostaje
  BEZ ZMIAN** — `render_coordinator_blockers(...) ==
  [Blocker("A", "DAY_SHIFT_OFF-01")]` — to jest test na dzisiejszy,
  naprawiany właśnie błąd; ma się zmienić na oczekiwanie polskiego
  tekstu z sekcji 3), `:148, :230, :286`.
- `tests/test_audit_r20_r21_findings.py:104,139`
- `tests/test_audit_r25_findings.py:63`
- `tests/test_audit_r26_findings.py:117,156`
- `tests/test_t018.py:588` (i `:573` — ten sam wzorzec co test_t013.py:138,
  dziś oczekuje surowego `"DAY_SHIFT_OFF-01"`)
- `tests/test_t009_open_and_assembler.py:92` — sprawdza podciąg
  `"quarter carry-in reset to 0"` w warningach; zmienić na sprawdzenie
  nowego polskiego tekstu (albo węższego, stabilnego fragmentu z niego).

**Wyraźnie NIE dotykać** `tests/test_t017.py:525` — sprawdza inny,
niezwiązany mechanizm: SOFT warning solvera
(`rota/planning/solver.py:670-673`, `_collect_warnings`), który też
zawiera tekst `"DAY_SHIFT_OFF-01 SOFT: ..."`, ale to wewnętrzny warning
listy planowania, nie treść blokera DECISION_REQUIRED z
`decision_guidance.py`. Ten string zostaje bez zmian — poza zakresem tego
Tasku (nie był zgłoszony, nie ma zatwierdzonego przez OWNERA zamiennika).

## 7. PREIMPLEMENTATION REDUCTION GATE

| Element | Źródło | Minimalna konieczna zmiana |
|---|---|---|
| carry-in warning | dokładny przykład OWNERA | zmiana treści jednego stringa |
| DAY_SHIFT_OFF-01 + checkbox | audyt Cursora V-B8 (nienaprawiony) + ten audyt | 4 wpisy w istniejącym słowniku, usunięcie jednego warunku |
| wersja/status | dokładny przykład OWNERA | usunięcie jednego `<span>`, jedna mapa etykiet, 2 miejsca użycia |
| demand_id/employee_id w Decyzjach | ten audyt | usunięcie jednego stringa, jeden fetch rosteru (wzorowany na istniejącym), jedna funkcja pomocnicza |
| wartość enuma w Historii | ten audyt | jedna mapa jednowierszowa, jedno miejsce użycia |

Usunięte z propozycji jako zbędne: tłumaczenie `coordinator_id` (poza
zakresem, sekcja 1), nowy endpoint listy koordynatorów, akcja naprawcza
dla `DAY_SHIFT_OFF-01` w `_ACTION_TEMPLATES`, wyczerpujące tłumaczenie
wszystkich możliwych wartości enumów w `History.tsx`, zmiana solvera/API,
ogólny refaktor którejkolwiek z tych czterech warstw.

## 8. TASK_SCOPE

Dozwolony kod produktu:

- `rota/application/assembler.py`
- `rota/planning/decision_guidance.py`
- `frontend/src/screens/MonthlyPlanning.tsx`
- `frontend/src/screens/Decisions.tsx`
- `frontend/src/screens/History.tsx`

Dozwolone testy i dokumenty:

- `tasks/ROTA-T048/brief.md`
- dokładnie sześć plików testowych wymienionych w sekcji 6a (aktualizacja
  oczekiwanego tekstu na nowe zatwierdzone brzmienie, nie nowej logiki;
  `test_t017.py` NIE jest na tej liście i nie wolno go dotykać):
  `tests/test_t013.py`, `tests/test_t018.py`,
  `tests/test_t009_open_and_assembler.py`,
  `tests/test_audit_r20_r21_findings.py`, `tests/test_audit_r25_findings.py`,
  `tests/test_audit_r26_findings.py`
- nowe testy jednostkowe/komponentowe wyłącznie dla zmienionego tekstu/
  etykiet powyżej

Poza zakresem, wymaga zatrzymania i wskazania konkretnej konieczności:

- `api/**` (żaden endpoint się nie zmienia)
- `rota/planning/**` poza `decision_guidance.py`, solver, walidator
- jakikolwiek mechanizm rozpoznawania/listowania koordynatorów
- `_ACTION_TEMPLATES` w `decision_guidance.py`
- inne ekrany niż wymienione trzy

## 9. WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS:
  - `rota/application/assembler.py --symbol _carry_in_before`
  - `rota/planning/decision_guidance.py --symbol _render_condition`
  - `frontend/src/screens/MonthlyPlanning.tsx --symbol resolveWarningText` (kontekst wzorca id→nazwa, nie modyfikowany)
  - `frontend/src/screens/Decisions.tsx --symbol DecisionDetail`
  - `frontend/src/screens/History.tsx --symbol renderStateValue`
- REASON: Task zmienia istniejących właścicieli prezentacji tekstu
  koordynatorowi; trzeba potwierdzić że każdy z nich ma jedno miejsce
  definicji i nie tworzyć drugiej ścieżki prezentacji.

Wykonane na `BASE_MAIN_SHA` (`where.py`): `_carry_in_before` — jedna
definicja, jeden produkcyjny caller w tym samym pliku (linia 160).
`_render_condition` — jedna definicja, jeden produkcyjny caller w tym
samym pliku (linia 83). Frontendowe symbole nie mają odpowiednika
`where.py`'s analizy top-level Python — sprawdzone ręcznie czytaniem
plików na exact SHA, po jednym miejscu użycia każdy.

## 10. Macierz odbioru

- **T48-01 — carry-in po polsku:** brak `target_hours` we wcześniejszym
  miesiącu kwartału daje warning w całości po polsku, zgodny z
  zatwierdzonym brzmieniem z sekcji 2; zero zmiany zwracanej wartości
  `carry_in` (nadal `0`).
- **T48-02 — DAY_SHIFT_OFF-01 po polsku:** blocker z tym kodem daje
  `"Koliduje z zapisem: Wolne w dzień"`, nie surowy kod.
- **T48-03 — bez „checkbox”:** `UNAVAILABLE-01`/`DAY_ONLY-01`/`SHIFT-24-01`
  dają teksty z sekcji 3, żaden nie zawiera słowa „checkbox”.
- **T48-04 — brak zmiany innych warunków:** `SICK_LEAVE-01`,
  `LEAVE_GRANTED-01`, `REST-01`, `LOAD-01`, `EXTERNAL-01`,
  `EXTERNAL_SUPPORT_DISABLED`, `NIGHT-STREAK-01` dają dokładnie te same
  teksty co przed Taskiem.
- **T48-05 — status po polsku, bez ID:** `MonthlyPlanning.tsx` nie renderuje
  nigdzie surowego `version_id` w widocznym tekście; status wersji bieżącej
  i każdej wersji w historii pokazuje etykietę z sekcji 4, nie surową
  wartość enuma.
- **T48-06 — Decyzje bez surowych ID:** blocker i load_blocker pokazują
  imię i nazwisko pracownika (z rosteru), nie `employee_id`; blokująca
  zmiana pokazuje tylko zakres dat, bez `demand_id`. Nieznany
  `employee_id` (spoza rosteru) nadal wyświetla się (fallback), nie
  wywala wyjątku.
- **T48-07 — reżim planowania w Historii:** wpis zmiany z
  `planning_regime: "ORDINARY"` w widoku „Przed/Po” pokazuje „standardowy”,
  nie `ORDINARY`; wartość `"OCHRONA"` pokazuje się bez zmian (już polska).
- **T48-08 — `requested_by` nienaruszone:** `Decisions.tsx` linia 52 i
  odpowiedniki w `History.tsx` nadal pokazują surowy `coordinator_id` —
  potwierdzenie, że ten Task świadomie tego nie dotyka.

## 11. Weryfikacja proporcjonalna do zmiany

Implementator uruchamia:

- celowane T48-01…T48-08 (nowe testy jednostkowe/komponentowe dla
  zmienionego tekstu tam, gdzie sensowne — backend łatwo testowalny przez
  istniejące fixture'y `assembler.py`/`decision_guidance.py`; frontend
  przez najprostszy dostępny w repo mechanizm testowania komponentów, jeśli
  istnieje, inaczej ręczna weryfikacja w przeglądarce z opisem w DELIVERY);
- istniejące testy dotykające `_carry_in_before`/`_render_condition`, jeśli
  asercje literalnie sprawdzają stary angielski tekst — zaktualizować
  oczekiwaną treść, nie logikę;
- `ruff check` dla zmienionych plików `.py`;
- lintowanie/typecheck frontendu, jeśli repo ma taki krok skonfigurowany;
- `git diff --check`.

Pełna suita repozytorium jest opcjonalna i wymaga osobnej zgody OWNERA.

## 12. Proces i oczekiwany werdykt CC

Pięć niezależnych, nienachodzących się na siebie zamian tekstu/etykiet w
czterech plikach. Żadna nie zmienia sygnatury funkcji używanej gdzie
indziej, żadna nie dodaje nowego stanu poza jednym fetchem rosteru w
`Decisions.tsx` (wzorowanym 1:1 na istniejącym w `MonthlyPlanning.tsx`).
Architekt nie jest potrzebny, chyba że CC wykaże konkretną sprzeczność
ownership.

Oczekiwany werdykt preimplementation:

- `PASS — READY_FOR_IMPLEMENTATION`, albo
- `FAIL` tylko z konkretnym `TRACE`, `OWNERSHIP` i reproduktorem sprzeczności.

Do PASS: CC READ-ONLY.

## 13. EXACT TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-T048/brief.md
- rota/application/assembler.py
- rota/planning/decision_guidance.py
- frontend/src/screens/MonthlyPlanning.tsx
- frontend/src/screens/Decisions.tsx
- frontend/src/screens/History.tsx
- tests/test_t013.py
- tests/test_t018.py
- tests/test_t009_open_and_assembler.py
- tests/test_audit_r20_r21_findings.py
- tests/test_audit_r25_findings.py
- tests/test_audit_r26_findings.py
