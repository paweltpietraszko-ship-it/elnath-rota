# ROTA-T050 — dwa martwe testy sprawdzające dawno nieaktualny tekst

STATUS: PROPOZYCJA DO WERYFIKACJI CC — ZERO KODU PRODUKTU — IMPLEMENTACJA
DOPIERO PO PASS PREIMPLEMENTATION AUDIT

BASE_MAIN_SHA: `1c8a926611dc9b187fab02f371ef58549ec8377b`

Źródło: oba znaleziska wypłynęły przypadkiem przy audytach implementacji
T048 i T049 (Codex), niezwiązane z tymi Taskami — zgłoszone osobno do
backlogu CC (`project_small_findings_backlog_2026-08-31.md`, pozycje 13
i 14), teraz przerabiane na osobny mały Task. Zero zmiany zachowania
produktu w obu przypadkach — tylko testy sprawdzające tekst, który już
dawno nie istnieje.

## 1. Cel

Naprawić dwa niezależne, zepsute testy, które od dawna sprawdzają
nieaktualny tekst zamiast tego, co program faktycznie dziś robi.

## 2. `test_t009_open_and_assembler.py` sprawdza dawno przetłumaczony tekst

`tests/test_t009_open_and_assembler.py:92`
(`test_5_missing_target_hours_not_invented_and_demand_count_unchanged`)
filtruje warningi przez podciąg `"omitted from WorkBalance context"`.
`rota/application/assembler.py` nigdzie już takiego tekstu nie zwraca —
ten sam warning jest dziś (`assembler.py:154-158`, komentarz cytuje
`OWNER-T041-01/C-05`) w całości po polsku:

```python
f"Brak wpisanego miesięcznego limitu godzin (target_hours) dla "
f"pracownika {employee_id!r} w miesiącu {month.isoformat()} — "
"użyto awaryjnego, równego podziału godzin."
```

Test przez to zawsze dostaje pustą listę `omitted_warnings` i pada na
asercji `len(omitted_warnings) == len(pstate.employees) - 1`. Potwierdzone
uruchomieniem testu na `task/ROTA-T048@512130f` (kontrakt PASS sprzed
implementacji T048) — już wtedy czerwony, T048 tego nie spowodował.

### Wymagane zachowanie

Zamienić w linii 92 filtr `"omitted from WorkBalance context"` na
`"użyto awaryjnego, równego podziału godzin"` (stabilny, unikalny fragment
aktualnego polskiego tekstu — nie pełne zdanie, żeby nie łamać testu przy
drobnej kosmetycznej zmianie treści w przyszłości). Reszta testu (fixture,
pozostałe asercje) bez zmian — to jest naprawa nazwy filtra, nie logiki
testu.

## 3. `openSite` w helperze e2e czeka na zły nagłówek

`frontend/e2e/helpers.ts::openSite` (linia 24-27):

```tsx
export async function openSite(page: Page, displayName: string) {
  await page.getByText(displayName, { exact: true }).click();
  await page.getByRole("heading", { name: "Panel sterowania" }).waitFor();
}
```

Po kliknięciu w nazwę obiektu program otwiera domyślnie zakładkę
„Przegląd” (`Room.tsx:52`, `activeNav` startuje na `"Przegląd"`), nie
„Panel sterowania” — a `Overview.tsx` (komponent zakładki „Przegląd”) w
ogóle nie renderuje żadnego nagłówka `role="heading"` o żadnej nazwie
(sprawdzone całe pliki `Overview.tsx`/`Room.tsx`) — więc oczekiwanie na
nagłówek „Panel sterowania” nigdy się nie spełnia, dopóki coś innego nie
przełączy zakładki. Potwierdzone na kontrakcie PASS T049
(`task/ROTA-T049@bec6100`), przed implementacją T049 — nie jej wina.

**KOREKTA R2 (audyt R1, BLOCKER):** pierwsza wersja tego briefu błędnie
policzyła użytkowników — 7 wywołań w 5 plikach zamiast rzeczywistych **16
wywołań w dokładnie 3 plikach** (`diagnostics.spec.ts`: 1,
`monthly-planning.spec.ts`: 7, `shift-catalog.spec.ts`: 8). `t041-daily-workflow.spec.ts`,
`t042-local-date.spec.ts` i `t043-coordinator-confidence.spec.ts` w ogóle
NIE importują współdzielonego `openSite` — każdy z nich definiuje **własną,
lokalną** funkcję o tej samej nazwie (potwierdzone czytaniem: każda ma
wprost komentarz „NOT the shared helpers.ts openSite()"), nietykaną przez
ten Task.

Jeden z rzeczywistych 16 wywołań ujawnia prawdziwy błąd propozycji z R1:
`diagnostics.spec.ts:200-201` woła `openSite`, po czym **natychmiast**
klika `[data-diag-action="roster-add-open"]` bez własnej dalszej
nawigacji — ten przycisk jest częścią `ControlPanel.tsx` (zakładka „Panel
sterowania", pod-zakładka „obsada", `Room.tsx:56`'s
`controlPanelTab` domyślnie `"obsada"`), niewidoczny na „Przegląd". Zmiana
z R1 (czekanie na okruszek zamiast nagłówka) usuwa błędny warunek
oczekiwania, ale nie naprawia tego, że `openSite` nigdy nie nawiguje do
„Panel sterowania" — test nadal wisi na `roster-add-open` (odtworzone
przez audyt: `npm run test:e2e -- diagnostics.spec.ts -g "privacy canary"`,
1 failed, timeout dokładnie na tym selektorze).

**Rzeczywista przyczyna i poprawne rozwiązanie**, znalezione w kodzie:
lokalna kopia `openSite` w `t041-daily-workflow.spec.ts` (linia 14-27) ma
dokładnie ten sam komentarz-diagnozę i już to naprawia — klika w nawigację
„Panel sterowania", zanim czeka na jej nagłówek:

```tsx
async function openSite(page, displayName) {
  await page.getByText(displayName, { exact: true }).click();
  await page.locator('[data-diag-action="room-nav-control-panel"]').waitFor({ state: "visible" });
  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await page.getByRole("heading", { name: "Panel sterowania" }).waitFor();
}
```

Współdzielony `openSite` w `helpers.ts` nigdy nie miał tego kliknięcia —
to jest brakująca linia, nie zły wybór warunku oczekiwania.
`NAV_DIAG_ACTIONS["Panel sterowania"] === "room-nav-control-panel"`
(`Room.tsx:28`, `data-diag-action={NAV_DIAG_ACTIONS[item]}` na
`Room.tsx:113`) — potwierdzony, istniejący, stabilny selektor.

### Wymagane zachowanie

**KOREKTA R2**: dodać brakujące kliknięcie w nawigację „Panel sterowania"
przed czekaniem na jej nagłówek — dokładnie wzorzec z
`t041-daily-workflow.spec.ts` powyżej, przeniesiony do współdzielonego
helpera:

```tsx
export async function openSite(page: Page, displayName: string) {
  await page.getByText(displayName, { exact: true }).click();
  await page.locator('[data-diag-action="room-nav-control-panel"]').click();
  await page.getByRole("heading", { name: "Panel sterowania" }).waitFor();
}
```

To przywraca oryginalnie zamierzone zachowanie helpera (otworzyć obiekt I
wylądować na „Panel sterowania"), zamiast zmieniać na co innego czeka —
`diagnostics.spec.ts:200-201`'s `roster-add-open` staje się widoczny bez
żadnej zmiany w tym pliku.

## 4. Co świadomie zostaje bez zmian

- Domyślna zakładka „Przegląd” po otwarciu obiektu — bez zmian, to
  istniejące, zamierzone zachowanie produktu (`Room.tsx:52`), nie defekt.
  `openSite` ma teraz jawnie nawigować DALEJ z tej zakładki, nie zmieniać,
  gdzie produkt domyślnie ląduje.
- Żadna logika `assembler.py`/`Room.tsx`/`Overview.tsx`/`ControlPanel.tsx` —
  oba testy są naprawiane pod istniejące zachowanie, zero zmiany produktu.
- `t041-daily-workflow.spec.ts`, `t042-local-date.spec.ts`,
  `t043-coordinator-confidence.spec.ts` — mają własne, niezależne, lokalne
  kopie `openSite` (nie importują współdzielonej) — celowo nietykane,
  poza zakresem tego Tasku.
- Pozostałe 15 z 16 wywołań współdzielonego `openSite`
  (`monthly-planning.spec.ts` × 7, `shift-catalog.spec.ts` × 8) — bez
  zmian, korzystają z helpera bez modyfikacji własnego kodu; poprawka
  dodaje nawigację, której i tak każde z nich już się spodziewa pośrednio
  (klikają dalej wewnątrz „Panel sterowania" albo przez globalny sidebar,
  który działa niezależnie od aktywnej zakładki).

## 5. PREIMPLEMENTATION REDUCTION GATE

| Element | Źródło | Minimalna konieczna zmiana |
|---|---|---|
| test_t009 filtr tekstu | znalezisko z audytu T048, backlog #13 | zmiana jednego literału stringa w jednej asercji |
| openSite brakująca nawigacja | znalezisko z audytu T049, backlog #14, poprawione R2 po audycie T050 R1 | dodanie jednej brakującej linii (kliknięcie), wzorzec już istnieje w repo (`t041-daily-workflow.spec.ts`) |

Usunięte z propozycji jako zbędne: zmiana domyślnej zakładki po otwarciu
obiektu, dodanie nagłówka do `Overview.tsx` tylko po to, żeby stary test
przechodził, jakakolwiek zmiana produktu.

## 6. TASK_SCOPE

Dozwolone testy (brak kodu produktu w tym Tasku):

- `tasks/ROTA-T050/brief.md`
- `tests/test_t009_open_and_assembler.py`
- `frontend/e2e/helpers.ts`

**KOREKTA R2**: `frontend/e2e/diagnostics.spec.ts` dopisane wyłącznie do
celowanej weryfikacji (sekcja 9) — plik nie jest edytowany, poprawka w
`helpers.ts` ma sama naprawić jego test „privacy canary" bez zmiany jego
treści. Jeśli po implementacji ten test nadal by nie przechodził, to
sygnał, że poprawka `openSite` jest niewystarczająca — zatrzymać się i
zgłosić, nie edytować `diagnostics.spec.ts`, żeby obejść objaw.

Poza zakresem: jakikolwiek plik `rota/`, `api/`, lub ekran we
`frontend/src/` — oba testy naprawiane są pod istniejące, niezmieniane
zachowanie. `t041-daily-workflow.spec.ts`/`t042-local-date.spec.ts`/
`t043-coordinator-confidence.spec.ts` — mają własne lokalne `openSite`,
nietykane (sekcja 4).

## 7. WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS:
  - `frontend/e2e/helpers.ts --symbol openSite`
- REASON: Task zmienia zachowanie współdzielonego helpera e2e; trzeba
  potwierdzić wszystkich wołających przed zmianą, żeby żaden nie zakładał
  ukrytego efektu ubocznego starego (błędnego) warunku oczekiwania.

**KOREKTA R2**: wykonane ponownie i poprawnie na `BASE_MAIN_SHA`
(WHERE_MAP + odczyt importów, jak w audycie R1): współdzielony `openSite`
wołany w **16 miejscach w dokładnie 3 plikach** (`diagnostics.spec.ts`: 1,
`monthly-planning.spec.ts`: 7, `shift-catalog.spec.ts`: 8) — nie 7 w 5,
jak błędnie podawała R1. Trzy pozostałe pliki ze słowem „openSite" mają
własne, lokalne, nieimportowane definicje (sekcja 3/4).
`test_5_missing_target_hours_not_invented_and_demand_count_unchanged`
nie ma odpowiednika WHERE_MAP (to test, nie funkcja produktu z callerami) —
weryfikacja to samo uruchomienie testu przed i po zmianie.

## 8. Macierz odbioru

- **T50-01 — test_t009 zielony:** `test_5_missing_target_hours_not_invented_and_demand_count_unchanged`
  przechodzi; `omitted_warnings` faktycznie łapie polski tekst dla
  pozostałych pracowników bez wpisanego limitu.
- **T50-02 — openSite działa (KOREKTA R2 — 16, nie 7):** wszystkich 16
  testów e2e wołających współdzielony `openSite` nadal przechodzi, w tym
  jawnie `diagnostics.spec.ts`'s test „privacy canary" (linia 200-201),
  który wcześniej wisiał na `roster-add-open` (albo — jeśli pełny e2e
  runner niedostępny w środowisku implementatora — ręczna weryfikacja w
  przeglądarce z opisem w DELIVERY, jawnie zaznaczona).
- **T50-03 — brak regresji:** żaden inny test w żadnym z trzech plików nie
  zmienia wyniku; lokalne, niezależne kopie `openSite` w
  `t041-daily-workflow.spec.ts`/`t042-local-date.spec.ts`/
  `t043-coordinator-confidence.spec.ts` pozostają nietknięte i nadal
  przechodzą bez zmian.

## 9. Weryfikacja proporcjonalna do zmiany

Implementator uruchamia:

- `tests/test_t009_open_and_assembler.py` (cały plik, szybki);
- **KOREKTA R2**: `diagnostics.spec.ts` (przynajmniej test „privacy
  canary", linia 200-201 — dokładny reproduktor blockera z audytu R1),
  `monthly-planning.spec.ts` i `shift-catalog.spec.ts` — jeśli pełny e2e
  runner jest dostępny w środowisku implementatora, inaczej ręczna
  weryfikacja w przeglądarce z jawnym zaznaczeniem w DELIVERY;
- `ruff check tests/test_t009_open_and_assembler.py`;
- `git diff --check`.

Pełna suita repozytorium jest opcjonalna i wymaga osobnej zgody OWNERA.

## 10. Proces i oczekiwany werdykt CC

Dwie niezależne, zero-ryzykowne naprawy testów pod istniejące zachowanie
produktu. Architekt nie jest potrzebny.

Oczekiwany werdykt preimplementation:

- `PASS — READY_FOR_IMPLEMENTATION`, albo
- `FAIL` tylko z konkretnym `TRACE`, `OWNERSHIP` i reproduktorem sprzeczności.

Do PASS: CC READ-ONLY.

## 11. EXACT TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-T050/brief.md
- tests/test_t009_open_and_assembler.py
- frontend/e2e/helpers.ts
