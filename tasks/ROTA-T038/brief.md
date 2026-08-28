# ROTA-T038 — Symulator Koordynatora (property-based test flow całego programu)

Status: **IMPLEMENTACJA ZAKOŃCZONA (autor: CC), do audytu**

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
