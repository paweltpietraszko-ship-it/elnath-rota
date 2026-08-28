# ROTA-T038 — Symulator Koordynatora (property-based test flow całego programu)

Status: **KOREKTA 2 ZAKOŃCZONA (autor: CC), do audytu Codex**

backend.py gate (na SHA `2d74efffee670a47f16ee7d3281e6ed7eb7f0b46`, przed
korektą 2): FAIL na `NEW_FILES: 3 new files (max 2)` + WYMAGA_DECYZJI na
`TOTAL_LINES: 385 lines changed`. **OWNER_ACCEPTED oba, Paweł, 2026-08-28.**
Bramka do ponownego uruchomienia na SHA po korekcie 2 (poniżej).

## KOREKTA 2 (OWNER_CORRECTED, 2026-08-28) — pełny przeprojekt

Pierwsza wersja (commit `f6d1b85`) była property-based benchmarkiem
oceniającym niezmienniki solvera. Paweł to skorygował wprost: **"nie
projektuj warstwy zarządzającej solverem, tylko cienką warstwę klikającą
ptaszki i reportującą"**. Pierwsza próba poprawki (jeden ustalony obiekt)
też odrzucona — chodziło o RÓŻNE wymyślone obiekty i scenariusze, nie jeden
sztywny przypadek.

Kluczowa zasada wyłoniona po kilku rundach dopytywania (na wyraźne
żądanie właściciela: "dopytuj dopóki masz wątpliwości, nie domyślaj się"):
**liczba pracowników na wymyślonym obiekcie musi wynikać z realnego
zapotrzebowania godzinowego tego obiektu, nigdy nie może być losowana
niezależnie od niego.** Paweł złapał dokładnie ten błąd w v1: `employee_count`
był tam losowany 4-8 niezależnie od zapotrzebowania, co mogło dać obiekt
"5-osobowy" z nazwy, a więcej osób w praktyce (np. przez niepoliczone
wsparcie zewnętrzne). Potwierdzone matematycznie na jego własnym przykładzie:
24h zmiana × 1 wymagana osoba × ~30 dni ≈ 720h/mies.; przy ~160h/mies./osobę
wychodzi ~5 osób — dokładnie liczba z jego przykładu.

Pełna przebudowa (`coordinator_simulator.py`/`test_coordinator_simulator.py`
zastąpione od zera, te same 3 pliki):
- generator NAJPIERW liczy zapotrzebowanie godzinowe (kształt zmiany D/N-12h
  vs pojedyncza 24h × liczba posterunków × dni miesiąca), POTEM wylicza
  obsadę (`ceil(godziny/160) + 1`) — nigdy losowana niezależnie;
- absencje (chorobowe/urlop/wolne na żądanie/niedostępność 24h) nadal
  losowane z ziarna, na dwóch fazach (przed PLAN, przed REPLAN);
- driver wyłącznie przez prawdziwe HTTP (`POST /workspace/sites`,
  `PUT .../shift-catalog`, `POST /workspace/employees`, `POST .../roster`,
  `POST .../support-window`, `POST /workspace/employees/{id}/availability`
  — realne "ptaszki" — `POST .../plan`, `.../select-candidate`, `.../replan`);
- **jedyna assercja: brak wyjątku/5xx.** Status i powód (PLAN/REPLAN) to
  fakty w raporcie, nie pass/fail;
- raport (`round_01/tests/simulator_report.md`) pokazuje na wpis:
  zapotrzebowanie, PEŁNĄ zadeklarowaną obsadę (lokalni+zewnętrzni razem),
  absencje, status+powód, i faktycznie użyte osoby — z jawną flagą
  "ROZBIEŻNOŚĆ" gdyby użyto kogoś spoza deklaracji. Weryfikacja przeze mnie
  na pełnym przebiegu (5 seedów): zero rozbieżności, dokładnie ten problem
  z v1 jest teraz obserwowalny wprost w raporcie, gdyby się powtórzył.

**Uproszczenie zgłoszone w trakcie budowy**: `posts` (liczba równoległych
posterunków) ustawione na stałe 1, nie losowane 1-3 jak pierwotnie
planowano — zmierzone: przy 2 posterunkach (10-12 deklarowanych osób) jeden
seed (PLAN+REPLAN) zajął ~90s, przy 1 (6-8 osób) ~90s też się zdarzyło ale
zwykle bliżej budżetu 45s/wywołanie — przy 10 seedach to realne ryzyko
kilkunastu minut. Zmienność zostaje w kształcie zmiany/regime/wsparciu
zewnętrznym/absencjach. `DEFAULT_SEED_COUNT` obniżone z 10 do 5 (każdy
seed robi PLAN+REPLAN, dwa pełne wywołania solvera, nie jedno jak w T037).

**Pełny formalny przebieg (5 seedów)**: `1 passed in 451.28s (0:07:31)`,
zero awarii, `simulator_report.md` dołączony do commita jako dowód.

Base implementation SHA: `37e32da6244e4e43f504ef44b9b5a290f05a21b7` (`main`,
po zmergowaniu T037).

Owner decision: Paweł, 2026-08-28 (rozmowa) — po trzech wcześniejszych,
niepełnych podejściach do testowania wertykalnego (R4 benchmark: zamrożony
5-osobowy model; `test_vertical_full_stack.py`: 4 ręczne scenariusze,
zatrzymuje się przed API; ręczne scenariusze Pawła: nie skalują się).
Cytat wytyczny: "Nie rób niczego, czego sam nie mógłbyś opisać swoimi
słowami" — stąd świadomy wybór własnej pętli po seedach zamiast biblioteki
`hypothesis` (pełny plan zaakceptowany w trybie plan mode tej samej sesji).

TASK_SCOPE:
- tests/property/__init__.py
- tests/property/coordinator_simulator.py
- tests/property/test_coordinator_simulator.py

Wszystkie trzy to nowe pliki (`tests/property/` nie istniał wcześniej) —
3 nowe pliki przekracza `MAX_NEW_FILES = 2` bramki `backend.py`. Wniosek
o akceptację niżej w sekcji weryfikacji.

## 1. Wynik dla właściciela

Jeden generator (`random_object_spec(seed, month)`) losuje z ziarna
realistyczny, ale zmienny obiekt: liczbę pracowników (4-8 na ~4/5 seedów,
1-2 na ~1/5 celowo), podzbiór DAY_ONLY, regime ORDINARY/OCHRONA, wsparcie
zewnętrzne, próg rolling-7d. Driver (`build_object` + testy) przepuszcza to
przez te same prawdziwe endpointy HTTP co przeglądarka koordynatora
(`api/routers/*.py` przez FastAPI TestClient): utwórz obiekt → katalog zmian
→ pracownicy → obsada → PLAN → (wybierz kandydata / zaakceptuj
DECISION_REQUIRED) → czasem ręczna korekta (NN) → finalizuj.

Wyrocznią jest wyłącznie już istniejący `rota.planning.validator.validate()`
— zero drugiego solvera, zero nowej architektury. Sprawdzane niezmienniki to
własne, już opublikowane obietnice kontraktu Roty (pełna lista w docstringu
`test_coordinator_simulator.py`), nie nowe wymagania.

## 2. Świadome uproszczenia względem zaakceptowanego planu (do wiadomości)

- **OCHRONA bez prawdziwego katalogu 24h** — używa tego samego katalogu D/N
  12h co ORDINARY; sam `Site.planning_regime=OCHRONA` już wystarczająco
  zmienia egzekwowanie REST/tygodniowego odpoczynku (potwierdzone w kodzie:
  `SitePlanningRegime` jest atrybutem Site, ortogonalnym do kształtu
  katalogu zmian). Budowa prawdziwej pary zmian 24h byłaby realnym,
  osobnym ryzykiem błędu bez dodatkowej wartości dla tego zakresu.
- **Brak losowych świąt w kalendarzu** — każdy dzień `holiday=False`, jak we
  wszystkich istniejących fixture'ach w repo. Odłożone, nie porzucone.
- **`required_primary_count` na stałe 1** dla D i N — warunek "wystarczająca
  obsada" opiera się na samej liczbie osób, nie na dokładnej matematyce
  pokrycia; wariant liczby wymaganych osób wymagałby prawdziwego
  przeliczenia pokrycia, żeby gwarancja FEASIBLE została uczciwa.
- **REPLAN wycięty z v1** — plan wspominał "czasem REPLAN" jako krok
  drivera; pominięty, żeby nie mnożyć złożoności/ryzyka w pierwszej rundzie.
  Niezmiennik #7 z planu (REPLAN nigdy nie rusza frozen/REALIZED) nie jest
  dziś sprawdzany przez ten symulator — pozostaje pokryty przez istniejący
  ręczny `test_12_freeze_affects_later_replan`, nie duplikowany tutaj.

## 3. Koszt (świadomy kompromis z tej sesji o czasie testów)

Jeden seed = jeden prawdziwy przebieg CP-SAT ≈ 45s (mierzone: seed=3, 8
pracowników). Domyślne uruchomienie pytest = 10 seedów (`DEFAULT_SEED_COUNT`)
≈ 7-8 minut. `ROTA_SIM_SEEDS=<N>` włącza głębszy przebieg do ręcznego
uruchomienia — NIE ma być domyślnie odpalane przy każdej iteracji CC.

## 4. Błędy znalezione i naprawione podczas budowy (własne, nie produktowe)

- `active_weekdays` w payloadzie katalogu zmian musi być ISO 1-7, nie 0-6
  (mój błąd, złapany na seedzie 3, naprawiony przed pełnym przebiegiem).
- Kontrola finalizacji z "błędnym" pustym zestawem `acknowledged_deviation_ids`
  była błędna dla seedów bez żadnych odchyleń (pusty zestaw jest wtedy
  POPRAWNY, nie błędny) — poprawione rozgałęzienie w teście (seed=1).

Żaden z tych dwóch błędów nie jest błędem produktu — oba były w logice
samego testu/generatora.

## 5. Poza zakresem

- Warstwa przeglądarki/UI — osobna sprawa (Playwright), nie ten mechanizm.
- Dokończenie gałęzi R5 benchmarku (`benchmark/real-object-architect-2026-08-13`).
- Refaktor z audytu PR #9.
- Losowe święta, wariancja `required_primary_count`, REPLAN w drivera —
  patrz punkt 2, kandydaci na kolejną rundę tego samego mechanizmu.

## 6. Weryfikacja

- `ruff check tests/property/` — czyste.
- Pojedyncze seedy uruchamiane osobno podczas budowy (seed=3, seed=2, seed=1)
  do szybkiego debugu zamiast pełnego przebiegu za każdym razem.
- Pełny domyślny przebieg (10 seedów) — jeden formalny run przed deliverym:
  **10 passed in 406.60s (0:06:46)**, zero regresji, zero flaki.
