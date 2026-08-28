# BRIEF — AUDIT-1: BASELINE KONTRAKTOWY NA DOKŁADNYM SHA

**Stan:** KOREKTA PO CODEX ROUND-1 REVIEW — nie wykonane, czeka na ponowną
aprobatę. Codex review: `arch/AUDIT_1_BASELINE_CODEX_REVIEW_2026-08-28.md`
(werdykt `WYMAGA_KOREKTY`, commit `96d8dd7`) — poprawki zastosowane niżej
(punkt 4 zawężony do wskazywania kandydatów, scenariusz 11 przeformułowany,
dodane ścieżki artefaktów).
**Źródło:** `START_HERE_CODE_INVENTORY_AUDIT_2026-08-28.md` (PR #9, autor:
Paweł), sekcja "6. Następne kroki audytu — kolejność obowiązkowa",
AUDIT-1 i AUDIT-2. Ten brief operacjonalizuje TYLKO AUDIT-1 — kolejne
kroki (AUDIT-2..6) zostają zaskopowane osobno, dopiero po zamknięciu
tego (reguła z samego dokumentu: "każdy kolejny AUDIT-N dopiero po
zamknięciu poprzedniego z dowodami, nie równolegle").
**BASE_SHA:** `d445ee6244e4e43f504ef44b9b5a290f05a21b7` (`main`, aktualny
HEAD — nie `aa6330c` z oryginalnego dokumentu, bo T037/T038/T039
zmieniły realny kod produktu od tego czasu).

## Dlaczego niezależność, nie CC

Paweł (2026-08-28): CC jest autorem większości tego kodu z tej i
poprzednich sesji — ma naturalne skrzywienie w stronę uznawania własnych
decyzji za rozsądne, ten sam mechanizm, przez który dziś (patrz
`ARCHITECT_BRIEF_NIGHT_STREAK_24H_FALSE_POSITIVE_2026-08-28.md`) przeoczył
interakcję H24/NIGHT-STREAK-01 przy budowaniu. Rozróżnienie przyjęte w tym
briefie:

- **Mechaniczne zbieranie dowodów** (uruchomienie testów/benchmarków,
  zapis surowych wyników) — wykonuje CC, bezosądowo, jak `backend.py`.
- **Ocena** (co jest SUSPECT, co ciąć, czy dana warstwa ma sens) — NIE
  jest częścią tego briefu. AUDIT-1 produkuje wyłącznie tabelę
  PASS/FAIL/ERROR, "bez naprawiania kodu w tym samym kroku" (dokument
  źródłowy, dosłownie).

## Co dokładnie ma zrobić CC (mechanicznie, bez interpretacji)

Na dokładnie `BASE_SHA` powyżej, w tej kolejności, każdy krok jako osobny
zapis wyniku (nie zatrzymywać się na pierwszym FAIL — zebrać wszystkie):

1. **Pełny `pytest`** — cała suita, nie scoped. Zapisać: liczbę
   PASS/FAIL/ERROR, listę nazw nieudanych testów, czas trwania.
2. **Benchmark PlanningEngine** (`README.md`, sekcja "Automatyczny
   benchmark"): `python -m benchmarks.rota_stress --cases 100 --seed
   20260812 --json <plik>`. Zapisać surowy JSON + skrócone podsumowanie.
3. **Real-object vertical scenario** (`benchmarks/real_object.py`,
   `README.md`/`REAL_OBJECT_BENCHMARK.md`): `python -m
   benchmarks.real_object --suite all --json <plik>`. Zapisać surowy
   JSON + skrócone podsumowanie.
4. **10 minimalnych scenariuszy CM0/CM1** z AUDIT-2 (dokument źródłowy,
   dosłownie, ponumerowane 1-10 poniżej) — dla KAŻDEGO CC wskazuje
   WYŁĄCZNIE kandydatów w formacie `plik::nazwa_testu` (grep/wyszukiwanie,
   zero czytania asercji pod kątem "czy to naprawdę pokrywa"), albo zapisuje
   `BRAK KANDYDATA`, jeśli nic nie znalazł. CC **nie orzeka** `POKRYTE`,
   **nie decyduje**, że potrzebny jest nowy test, i **nie pisze** żadnego
   nowego testu w tej rundzie (Codex round-1 review, `WYMAGA_KOREKTY`,
   2026-08-28: to był osąd kontraktowy autora, nie czynność mechaniczna).
   Klasyfikację `POKRYTE / CZĘŚCIOWE / BRAK` (sprawdzenie asercji i
   rzeczywistego łańcucha produkcyjnego) robi Codex po zebraniu wyników,
   nie CC.
   1. zwykły realny miesiąc 5 pracowników, D/N, pełne coverage;
   2. DAY_ONLY employee nie dostaje N;
   3. zgłoszona choroba jednego pracownika w już istniejącym planie →
      REPLAN zachowuje REALIZED/frozen i próbuje naprawić przyszłość;
   4. jednocześnie co najmniej jeden dzień wolny/urlop innej osoby;
   5. brak personelu → DECISION_REQUIRED, nie TECHNICAL_ERROR i nie
      fałszywe FEASIBLE;
   6. rolling 7d > threshold → plan nie kończy jako zwykłe FEASIBLE;
   7. REST boundary między miesiącami;
   8. restart/reopen → current schedule rekonstruuje się identycznie;
   9. manual correction → nowa wersja, poprzedni FINAL nie jest
      mutowany;
   10. invalid model/config → TECHNICAL_ERROR, nie decyzja kadrowa.

## Proponowana 11. pozycja (do aprobaty Codex, nie zaimplementowana)

Znalezisko z tej samej sesji (`ARCHITECT_BRIEF_NIGHT_STREAK_24H_FALSE_POSITIVE_2026-08-28.md`,
dowód: ręczna rotacja 5 osób przechodzi `validate()` na czysto, solver
mimo to zwraca `DECISION_REQUIRED`) sugeruje brakującą pozycję w AUDIT-2.

**Treść zaakceptowana przez Codexa (round-1 review, 2026-08-28), dokładny
CM0 bez tautologii "wystarczająca obsada":**

> 11. Wrzesień 2026, OCHRONA, jedna codzienna zmiana H24 06:00–06:00,
>     pięciu aktywnych LOCAL, target 176 h, wszyscy dostępni, bez
>     dodatkowych reguł i wcześniejszego grafiku → PLAN zwraca FEASIBLE,
>     a kandydat przechodzi produkcyjny `validate()`.

Nie wolno rozszerzać tego do twierdzenia "H24 nigdy nie zwraca
DECISION_REQUIRED" — przy absencji, niedostępności lub aktywnej regule
pracownika taki wynik może być prawidłowy (Codex, tamże).

CC nie dodaje tego samodzielnie do listy źródłowego dokumentu — to
propozycja do jawnej akceptacji/odrzucenia przez Pawła w tej rundzie, nie
fakt dokonany. (Uwaga: równolegle powstał już `task/ROTA-T040` z
konkretną poprawką tego dokładnego defektu — patrz `tasks/ROTA-T040/brief.md`
— więc do czasu jego zamknięcia scenariusz 11 prawdopodobnie i tak
przejdzie z FAIL na PASS niezależnie od AUDIT-1.)

## Format wyniku

Konkretne ścieżki surowych artefaktów (Codex round-1 review):

- `tasks/ROTA-AUDIT1/round_01/tests/pytest.txt` — pełny surowy output.
- `tasks/ROTA-AUDIT1/round_01/tests/rota_stress.json` — surowy `--json`.
- `tasks/ROTA-AUDIT1/round_01/tests/real_object.json` — surowy `--json`.
- `tasks/ROTA-AUDIT1/round_01/tests/cm0_cm1_candidates.md` — lista
  kandydatów `plik::nazwa_testu` / `BRAK KANDYDATA` per scenariusz 1-11.
- `tasks/ROTA-AUDIT1/round_01/tests/baseline_report.md` — jeden raport
  zbiorczy, odsyłający do powyższych: krok → exact SHA → dokładna komenda
  → kod wyjścia → czas trwania → jedno zdanie faktu z surowego wyniku, bez
  interpretacji "co to znaczy" ani rekomendacji cięcia. PASS/FAIL
  benchmarku oznacza wyłącznie wynik istniejącego narzędzia — nie jest
  samodzielnym werdyktem zgodności produktu z PRODUCT_TRUTH.

## Poza zakresem tego briefu

- AUDIT-2 jako osobny krok wykonawczy (pisanie NOWYCH testów dla
  scenariuszy bez pokrycia) — dopiero po zamknięciu AUDIT-1 z dowodami.
- AUDIT-3..6 (reachability, duplikacja, complexity budget, owner decision
  queue) — nie zaskopowane tutaj.
- Jakakolwiek naprawa kodu wynikająca z FAIL znalezionych w tym kroku —
  AUDIT-1 tylko mierzy i raportuje.

## Warunek uruchomienia

Ten brief NIE jest wykonywany, dopóki Codex go nie zaaprobuje (poprawi
zakres/kolejność/format, jeśli uzna to za niewystarczające lub
niezgodne z dokumentem źródłowym). Dopiero po aprobacie: `task_init.py
ROTA-AUDIT1`, wykonanie kroków 1-4 mechanicznie, `backend.py` nie
dotyczy (brak zmian w kodzie produktowym, tylko raport).
