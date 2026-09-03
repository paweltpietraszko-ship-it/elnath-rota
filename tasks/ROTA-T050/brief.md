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

Sprawdzone bezpiecznie: wszystkie 7 wywołań `openSite` w plikach e2e
(`diagnostics.spec.ts`, `monthly-planning.spec.ts`, `shift-catalog.spec.ts`
i inne) od razu po nim wołają własną, dalszą nawigację (`openMonthlyPlanning`,
`openObiektTab`, kliknięcie konkretnej akcji) — żaden nie zakłada, że
`openSite` samo zostawia ekran na „Panel sterowania”. Zmiana warunku
oczekiwania w `openSite` nie zmienia więc sensu żadnego wywołującego testu.

### Wymagane zachowanie

Zamienić czekanie na nagłówek na czekanie na okruszek (breadcrumb) z nazwą
obiektu — dokładnie ten sam idiom, którego `createSite` już używa do
potwierdzenia sukcesu (`helpers.ts:21`, `getByText(displayName, {
exact: true }).waitFor()`), tu zastosowany po wejściu do pokoju obiektu
zamiast po jego utworzeniu:

```tsx
export async function openSite(page: Page, displayName: string) {
  await page.getByText(displayName, { exact: true }).click();
  await page.getByText(displayName, { exact: true }).waitFor();
}
```

(po kliknięciu karta obiektu na liście znika, a ten sam tekst pojawia się
w okruszku `.room-breadcrumb-current` — jedno dopasowanie, bez ryzyka
niejednoznaczności trybu strict Playwrighta).

## 4. Co świadomie zostaje bez zmian

- Domyślna zakładka „Przegląd” po otwarciu obiektu — bez zmian, to
  istniejące, zamierzone zachowanie produktu (`Room.tsx:52`), nie defekt.
- Żadna logika `assembler.py`/`Room.tsx`/`Overview.tsx` — oba testy są
  naprawiane pod istniejące zachowanie, zero zmiany produktu.
- Pozostałe 7 wywołań `openSite` w plikach spec — bez zmian, korzystają z
  helpera bez modyfikacji własnego kodu.

## 5. PREIMPLEMENTATION REDUCTION GATE

| Element | Źródło | Minimalna konieczna zmiana |
|---|---|---|
| test_t009 filtr tekstu | znalezisko z audytu T048, backlog #13 | zmiana jednego literału stringa w jednej asercji |
| openSite warunek oczekiwania | znalezisko z audytu T049, backlog #14 | zamiana jednej linii na już istniejący w tym samym pliku idiom |

Usunięte z propozycji jako zbędne: zmiana domyślnej zakładki po otwarciu
obiektu, dodanie nagłówka do `Overview.tsx` tylko po to, żeby stary test
przechodził, jakakolwiek zmiana produktu.

## 6. TASK_SCOPE

Dozwolone testy (brak kodu produktu w tym Tasku):

- `tasks/ROTA-T050/brief.md`
- `tests/test_t009_open_and_assembler.py`
- `frontend/e2e/helpers.ts`

Poza zakresem: jakikolwiek plik `rota/`, `api/`, lub ekran we
`frontend/src/` — oba testy naprawiane są pod istniejące, niezmieniane
zachowanie.

## 7. WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS:
  - `frontend/e2e/helpers.ts --symbol openSite`
- REASON: Task zmienia zachowanie współdzielonego helpera e2e; trzeba
  potwierdzić wszystkich wołających przed zmianą, żeby żaden nie zakładał
  ukrytego efektu ubocznego starego (błędnego) warunku oczekiwania.

Wykonane na `BASE_MAIN_SHA` (`git grep`): `openSite` wołane w 7 miejscach
w 5 plikach spec (sekcja 3) — każde z osobną, dalszą nawigacją zaraz po
wywołaniu. `test_5_missing_target_hours_not_invented_and_demand_count_unchanged`
nie ma odpowiednika WHERE_MAP (to test, nie funkcja produktu z callerami) —
weryfikacja to samo uruchomienie testu przed i po zmianie.

## 8. Macierz odbioru

- **T50-01 — test_t009 zielony:** `test_5_missing_target_hours_not_invented_and_demand_count_unchanged`
  przechodzi; `omitted_warnings` faktycznie łapie polski tekst dla
  pozostałych pracowników bez wpisanego limitu.
- **T50-02 — openSite działa:** każdy z 7 testów e2e wołających `openSite`
  nadal przechodzi (albo — jeśli pełny e2e runner niedostępny w
  środowisku implementatora — ręczna weryfikacja w przeglądarce z opisem
  w DELIVERY, jawnie zaznaczona).
- **T50-03 — brak regresji:** żaden inny test w obu plikach nie zmienia
  wyniku.

## 9. Weryfikacja proporcjonalna do zmiany

Implementator uruchamia:

- `tests/test_t009_open_and_assembler.py` (cały plik, szybki);
- e2e specy wołające `openSite`, jeśli pełny runner jest dostępny w
  środowisku implementatora — w przeciwnym razie ręczna weryfikacja z
  jawnym zaznaczeniem w DELIVERY;
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
