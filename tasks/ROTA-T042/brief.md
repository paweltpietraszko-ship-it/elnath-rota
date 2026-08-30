# ROTA-T042 — małe naprawy po AUDIT-4

Status: **PROPOZYCJA DLA ARCHITEKTA — ZERO KODU PRODUKTU — CC READ-ONLY DO
PASS PREIMPLEMENTATION AUDIT**

BASE_MAIN_SHA: `071feb7cfaead0dbe8f514184fcb5ea614fa1cbf`

Źródła:

- `audit/ROTA-AUDIT4@0a1ef882a762965f4fd83632c905df7dd0dac2d2`,
  `tasks/ROTA-AUDIT4/round_01/tests/tests_r1.txt`, punkty 8–10;
- niezależne potwierdzenie Codexa
  `audit/ROTA-AUDIT4-REVIEW@b4a7e4605c1c5a5fad9fb9b63258debd30adbb28`;
- OWNER 2026-08-30: najpierw naprawy produktu po AUDIT-4, potem osobny task
  naprawiający Symulator Koordynatora na poprawionym `main`.

## 1. Cel i granica zachowania

Trzy checkpointy, trzy logiczne commity:

1. **A — data lokalna:** ekrany używają lokalnego dnia/miesiąca, nie UTC;
2. **B — PlanningState:** PLAN i REPLAN nie wykonują dwóch identycznych
   odczytów, gdy pierwszy wynik jest odrzucany;
3. **C — decyzje API:** dwa endpointy używają jednego adaptera wspólnej treści
   `DecisionRequiredPayload`.

Tylko A zmienia widoczny, błędny wynik. „Dzisiaj” oznacza datę kalendarzową na
komputerze koordynatora. O 00:30 czasu polskiego 1 września program ma pokazać
1 września i wrzesień, choć w UTC jest jeszcze 31 sierpnia. Naprawa nie czyta,
nie zapisuje ani nie wysyła nowych danych; pola pozostają edytowalne.

B i C są `TECHNICAL_ONLY`. Nie zmieniają solvera, wersjonowania, publicznych
odpowiedzi API ani treści decyzji.

## 2. Checkpoint A — lokalna data

Jedna mała funkcja w `frontend/src/localDate.ts` formatuje lokalny `Date` jako
`YYYY-MM-DD` przez `getFullYear()`, `getMonth()` i `getDate()`. Nie używa
`toISOString()` do ustalania lokalnego dnia. Cztery wadliwe ekrany korzystają
z tego helpera:

- `Analytics.tsx`;
- `Export.tsx`;
- `MonthlyPlanning.tsx`;
- `Overview.tsx`.

AUDIT-4 wymienił pierwsze trzy. Codex znalazł `Overview.tsx:9` jako osiągalną
ścieżkę tej samej klasy błędu (`toISOString().slice(0, 7)`). To nie jest nowa
funkcja produktu, tylko pełne zamknięcie potwierdzonego defektu.

Macierz:

- **T42-A01:** `2026-08-31T22:30:00Z` w Europe/Warsaw daje
  `2026-09-01`, nie `2026-08-31`;
- **T42-A02:** Analytics, Export i Overview otwierają wrzesień 2026;
- **T42-A03:** MonthlyPlanning otwiera wrzesień, a domyślne daty REPLAN i
  korekty mają `2026-09-01`;
- **T42-A04:** zwykła godzina w środku dnia nadal daje właściwą datę;
- **T42-A05:** TypeScript i build są czyste.

Poza zakresem: poprawne lokalne obliczenia w `EmployeeDetail.tsx` i
`Workspace.tsx`; timestampy diagnostyczne, które mają pozostać UTC; ogólny
refaktor wszystkich użyć `Date`; nowa biblioteka dat.

## 3. Checkpoint B — jedno składanie stanu

Usunąć wyłącznie wywołania, których wyniki są odrzucane:

- pierwsze PLAN bez istniejącej wersji: obecnie `plan_ops.py:158`;
- REPLAN: obecnie `plan_ops.py:426`.

W obu ścieżkach pozostaje jedno `assemble_planning_state()`, nadal przed
pierwszym zapisem i dostarczające stan rzeczywiście używany dalej. Innych
wywołań assemblera nie zmieniać.

`tests/test_audit_t009_r5.py:249-288` wymusza awarię dokładnie przy drugim z
dwóch wywołań. To test kształtu starej implementacji. Należy go zmienić tak,
aby awaria jedynego odczytu nadal dowodziła braku nowej wersji i braku zmiany
current pointer. Nie wolno zachować martwego wywołania dla zielonego testu.

Macierz:

- **T42-B01:** pierwszy PLAN składa stan dokładnie raz przed zapisem;
- **T42-B02:** REPLAN składa stan dokładnie raz przed zapisem;
- **T42-B03:** wyjątek jedynego odczytu nie tworzy root/child WORKING i nie
  przesuwa current pointer;
- **T42-B04:** zwykły PLAN i REPLAN zachowują obecny wynik i ostrzeżenia.

Poza zakresem: cache, assembler, transakcje, lifecycle,
`create_schedule_version()`, solver i kolejność rzeczywistych zapisów.

## 4. Checkpoint C — jeden adapter treści decyzji

Obecnie `api/routers/schedule.py` i `api/routers/decisions.py` niezależnie
definiują trzy identyczne modele elementów oraz mapują te same cztery pola:

- `blocking_shift_demands`;
- `blockers`;
- `load_blocker`;
- `unblocking_options`.

Po T042 modele elementów i mapowanie mają jednego właściciela w warstwie
`api`. Router harmonogramu nadal zwraca `DecisionRequiredPayloadOut`. Router
decyzji nadal zwraca płaski `DecisionRequiredOut` z obecnymi metadanymi.

Nie wolno zmieniać nazw, typów, zagnieżdżenia ani obecności pól, dodawać
endpointu, drugiego odczytu, nowego use-case albo przenosić modeli Pydantic do
domeny/persistence/planning.

Macierz:

- **T42-C01:** dla jednej zapisanej decyzji cztery wspólne pola z GET miesiąca
  harmonogramu i GET szczegółów decyzji są równe;
- **T42-C02:** przypadki z `load_blocker` i bez niego zachowują obecny format;
- **T42-C03:** szczegóły nadal mają bez zmian `decision_required_id`,
  `site_id`, `month`, `schedule_version_id`, `requested_by`, `recorded_at` i
  `linked_action_ids`;
- **T42-C04:** odpowiedź PLAN i odczyt po odświeżeniu zachowują kształt;
- **T42-C05:** `frontend/src/api/client.ts` nie wymaga zmiany.

Test porównuje prawdziwe odpowiedzi endpointów; nie jest testem tekstu źródła.

## 5. PREIMPLEMENTATION REDUCTION GATE

| Element | Źródło i konieczność | Minimalny wynik |
|---|---|---|
| helper daty | AUDIT-4 + wynik widoczny OWNER | jeden helper, tylko cztery wadliwe ekrany |
| martwe odczyty | AUDIT-4 punkt 8 | skasowanie dwóch linii + poprawa starego testu |
| adapter decyzji | AUDIT-4 punkt 9 | jeden mały moduł API, bez zmiany DTO/endpointów |
| test A | błąd granicy lokalnego dnia | jeden targeted Playwright |
| test B | bezpieczeństwo wersji | istniejący test atomowości + licznik jednego odczytu |
| test C | dwa osiągalne endpointy | jeden pion API obu odpowiedzi |

Odrzucono: nowe encje/pola/endpointy, zmiany klienta TS, bibliotekę dat, cache,
refaktor solvera/API/frontendu, testy źródłowe oraz naprawę Symulatora w T042.

## 6. TASK_SCOPE

TASK_SCOPE:

- `frontend/src/localDate.ts` (nowy);
- `frontend/src/screens/Analytics.tsx`;
- `frontend/src/screens/Export.tsx`;
- `frontend/src/screens/MonthlyPlanning.tsx`;
- `frontend/src/screens/Overview.tsx`;
- `frontend/e2e/t042-local-date.spec.ts` (nowy);
- `rota/application/plan_ops.py`;
- `tests/test_audit_t009_r5.py`;
- `api/decision_payload.py` (nowy);
- `api/routers/schedule.py`;
- `api/routers/decisions.py`;
- `tests/test_t042_audit4_repairs.py` (nowy).

To maksymalny zakres, nie nakaz dotknięcia każdego pliku. Inny plik produktu
wymaga zatrzymania i wskazania blokera przed edycją.

Zakazane: `rota/planning/**`, schema/migracje/persistence,
`frontend/src/api/client.ts`, inne ekrany/helpery dat, zmiana zachowania
PLAN/REPLAN/DecisionRequired, T038 oraz porządki niezwiązanych fragmentów.

## 7. WHERE_MAP

WHERE_MAP:

- MODE: REQUIRED
- TARGETS:
  - `frontend/src/screens/Analytics.tsx --symbol todayIso`
  - `frontend/src/screens/Export.tsx --symbol todayIso`
  - `frontend/src/screens/MonthlyPlanning.tsx --symbol todayIso`
  - `frontend/src/screens/Overview.tsx --symbol currentYearMonth`
  - `rota/application/plan_ops.py --symbol plan_month`
  - `rota/application/plan_ops.py --symbol replan`
  - `api/routers/schedule.py --symbol DecisionRequiredPayloadOut`
  - `api/routers/schedule.py --symbol _decision_payload_out`
  - `api/routers/decisions.py --symbol DecisionRequiredOut`
- REASON: Task usuwa kopie helperów/adapterów i zmienia ich ownera; raw hits
  mają ujawnić pozostawioną osiągalną kopię.

Wykonane na BASE_MAIN_SHA:

```text
python where.py rota/application/plan_ops.py
python where.py rota/application/plan_ops.py --symbol plan_month
python where.py rota/application/plan_ops.py --symbol replan
python where.py api/routers/schedule.py
python where.py api/routers/schedule.py --symbol DecisionRequiredPayloadOut
python where.py api/routers/schedule.py --symbol _decision_payload_out
python where.py api/routers/decisions.py
python where.py api/routers/decisions.py --symbol DecisionRequiredOut
python where.py frontend/src/screens/Analytics.tsx --symbol todayIso
python where.py frontend/src/screens/Export.tsx --symbol todayIso
python where.py frontend/src/screens/MonthlyPlanning.tsx --symbol todayIso
python where.py frontend/src/screens/Overview.tsx --symbol currentYearMonth
```

`where.py` nie klasyfikuje importowanego `assemble_planning_state` jako symbolu
top-level `plan_ops.py`; ręczne czytanie potwierdziło pary 158–159 i 426–427
oraz brak operacji pomiędzy nimi. Nowe pliki nie istnieją na bazie; po
implementacji audytor sprawdza faktycznie dodane symbole. Raw hits nie są
werdyktem ownership.

## 8. Kolejność, testy i odbiór

Kolejność: A, potem B, potem C; osobne logiczne commity, bez refaktoru między
nimi.

Implementator uruchamia tylko:

- A: TypeScript/build + targeted T42-A;
- B: T42-B + wąska regresja wersjonowania PLAN/REPLAN;
- C: T42-C + istniejące testy API decyzji/harmonogramu.

Nie uruchamia pełnej suity po każdym checkpointcie. Codex wykonuje niezależne
minimalne piony, a pełną regresję tylko raz na końcowym SHA zgodnie z
`AGENTS.md`.

Gotowość do audytu wymaga: brak zmiany publicznego JSON/klienta TS, zamknięcie
macierzy A–C, `git diff --check`, czysty TypeScript/build oraz exact SHA.

Raport: `tasks/ROTA-T042/round_01/tests/tests_r<n>.txt`; nie nadpisywać
wcześniejszej rundy.
