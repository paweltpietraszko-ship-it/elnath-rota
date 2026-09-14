# ODLOZONE.md — rzeczy zauważone, świadomie odłożone

Backlog rzeczy, które CC lub Codex zauważyli, ale które NIE trafiają do
BOARD.md ani do pamięci CC między sesjami — żeby nie odżywały same z siebie
w każdej rozmowie. Ten plik czyta się tylko wtedy, gdy Paweł sam chce
wrócić do tematu. Jeden wpis = jedna sprawa, krótko, z datą i minimalnym
kontekstem żeby dało się to podjąć bez odtwarzania całej rozmowy.

Format wpisu:

```
## [data] Tytuł

Krótki opis (2-4 zdania). Dlaczego odłożone. Gdzie szukać więcej kontekstu
(plik, task, commit), jeśli trzeba wrócić.
```

---

## 2026-09-14 Kopiowanie katalogu ról między obiektami (sieć sklepów)

`ROTA-T065-CONFIGURABLE-ROLES` wprowadza katalog ról per obiekt, ale każdy
nowy obiekt zaczyna z pustym katalogiem — koordynator wpisuje role od
zera. Dla sieci kilku podobnych sklepów (np. żony Pawła, ~10 punktów)
powtarzanie tych samych ról (Kierownik, Sprzedawca) przy każdym nowym
obiekcie jest niewygodne.

Odłożone: świadoma decyzja przy starcie Tasku (2026-09-14) — "wystarczy
osobno" na pytanie o kopiowanie katalogu. Realny mechanizm byłby: przy
tworzeniu obiektu opcja "skopiuj katalog ról z istniejącego obiektu".
Podjąć dopiero jeśli powtarzalne wpisywanie ról realnie zacznie przeszkadzać
(kilka obiektów tej samej sieci pod rząd), nie teraz.

---

## 2026-09-09 Solver nie dokłada reszty grafiku wokół jednego zaakceptowanego wyjątku od HARD

Gdy koordynator świadomie akceptuje złamanie reguły HARD dla jednej osoby
(np. trzecia zmiana pod rząd, praca mimo urlopu pozostawionego na papierze),
jedyny dziś dostępny mechanizm (Ręczna korekta) nie używa solvera wcale —
trzeba by ręcznie wpisać przypisania dla całego pozostałego miesiąca, nie
tylko dla spornej zmiany. Realny mechanizm byłby: koordynator wskazuje
jeden wyjątek, PLAN dokłada resztę automatycznie (podobnie jak dziś działa
automatyczne emergency-24h dla REST-01, tylko sterowane przez koordynatora
per przypadek, nie z góry ustawione na roli pracownika).

Odłożone: to niewygodność, nie blokada — świadome naruszenie i tak da się
dziś zapisać, tylko wolniej. Osobna sprawa od realnej, węższej luki z
brakiem wersji grafiku przy pierwszym zablokowanym PLAN (ta poszła do
architekta jako `ROTA-T057-ROUTE-A-REGRESSION`, main@2f7c43c). Nie
podejmować bez konkretnego, powtarzającego się przypadku z życia.

---

## 2026-09-11 T063 może być fałszywie czerwony 1. dnia miesiąca przed pierwszą służbą

Znalezisko architekta przy końcowym PASS T063 (`task/ROTA-T063@305d069`,
main@f0a2ab5). Test opiera się na tym, że dzień 1 bieżącego miesiąca już
minął względem realnego zegara serwera, żeby `is_schedule_version_live`
było prawdziwe i przycisk „Przelicz (PLAN)” się pojawił (SCENARIO_PACK v0.3,
`frontend/e2e/t063-business-outcomes.spec.ts`). W wąskim oknie między
północą a startem pierwszej służby obiektu (u nas 05:00, godzina D-zmiany)
1. dnia miesiąca to założenie jest fałszywe — test uruchomiony akurat w tym
oknie dostałby fałszywy czerwony wynik, nie realny defekt produktu.

Odłożone: architekt nie blokuje przez to merge; naprawić dopiero, jeśli T063
ma być traktowane jako długowieczny test referencyjny uruchamiany
regularnie (np. w CI o stałej porze). Nie podejmować bez takiej decyzji —
naprawa to prawdopodobnie proste przesunięcie okna (np. start dnia 2, nie
dnia 1) albo świadome pominięcie testu w tym wąskim oknie czasowym.

---

## 2026-09-12 T059 — 24h SOFT tolerance equity bez regresji CP-SAT

Cel T059 był dobry (equity bez sztywnego progu), ale dwie niezależne próby
naprawy pokazały, że problem leży głębiej niż sam deadband. Cztery różne
enkodowania tego samego 24h dead-zone identycznie wysadzają CP-SAT (0.4s →
45s, budżet wyczerpany, solver nigdy nie dowodzi optymalności). Prostsza
alternatywa (podniesienie jednej stałej wagi `DN_RHYTHM_REWARD_WEIGHT` z 1
na 10, żeby rytm dominował equity) też natychmiast wysadza solver tak samo
— czyli problem nie jest w samym deadbandzie, tylko w całej architekturze
"wagi muszą się nawzajem dominować przez ogromne stałe": każda zmiana w
tym łańcuchu jest krucha. Pełny materiał dowodowy:
`arch/FINDING_2026-09-08_T058_EQUITY_DEADBAND_CPSAT_PERFORMANCE.md`.

Odłożone: właściwa naprawa wymagałaby przeprojektowania sposobu budowania
celu solvera (np. optymalizacja lexicographic/fazowa zamiast jednej ważonej
sumy) — duża, kosztowna praca badawcza, bez zgłoszonego realnego przypadku,
który by jej dziś wymagał. Nie podejmować bez konkretnego, powtarzającego
się przypadku z życia, w którym brak tej tolerancji faktycznie przeszkadza
koordynatorowi.

---

## 2026-09-14 Pozostałe 33 pre-existing failury w pełnym pakiecie testów

Pierwszy w tej sesji pełny `pytest tests/ --ignore=tests/property` (1439
testów) znalazł 64 pre-existing failures na `main`, niezwiązanych z
żadnym refaktorem tego dnia (potwierdzone bajt-w-bajt na czystym
worktree). 31 naprawionych tego samego dnia w `ROTA-ORDINARY-POSITION-
FIXTURE-FALLOUT` (mechaniczne: brak stanowiska ORDINARY, martwe literały
`LATEST_SCHEMA_VERSION`). Pozostałe 33, świadomie odłożone bez naprawy:

- **~28 testów: `DAY_ONLY-01`/`dn_semantics_apply` rozbieżności.** Np.
  `test_audit_r25_findings.py::test_r25_1a_...` oczekuje tekstu
  „Koliduje z ustawieniem: Nocka", dostaje tylko „Koliduje z zapisem:
  Chorobowe". Prawdopodobnie stare testy nieaktualne po zmianach
  `dn_semantics_apply` z ROTA-T065, ale niezweryfikowane — wymaga
  realnej analizy czy to zaniedbany test czy realny regres. Inne pliki
  z tą grupą: `test_t012.py`, `test_t013.py`, `test_t017.py` (2 z 3
  testów), `test_t022_planning_integrity.py` (6), `test_manual_audits.py`
  (3), `test_audit_t009_r4.py`, `test_audit_t010_r3.py`,
  `test_audit_t010_r5_b.py` (4), `test_t009_plan_select_replan.py`,
  `test_t010_day_only_n_exception.py` (2), `test_real_object_benchmark.py`,
  `test_replan_minimal_reshuffle.py`, `test_rota_generic_month.py`,
  `test_rota_stress_benchmark.py`.
- **3 testy: fałszywe alarmy w testach "no coupling".**
  `test_site_memory_decision_ledger.py::test_planning_engine_has_no_site_memory_coupling`,
  `test_site_profile_persistence.py::test_planning_engine_has_no_persistence_coupling`,
  `test_site_rules_execution.py::test_o_site_rules_module_has_no_persistence_or_sqlite_coupling`
  — skanują surowy tekst źródła (nie AST) szukając podciągu typu
  `"rota.persistence"`, łapią wzmiankę w docstringu
  `rota/planning/availability.py`, nie prawdziwy import. Wymaga decyzji:
  przepisać na AST czy przeredagować docstring (kruche, powtórzy się).
- 1 test celowo samo-unieważniający się (`test_t023_checkpoint_b.py::test_t23_54_...`)
  — diff-proof że `eligibility.py`/`constraints.py` niezmienione,
  złamany na stałe odkąd ROTA-T065-ORDINARY-TIME-AVAILABILITY legalnie
  zmienił `eligibility.py`. Nie wymaga akcji, chyba że ten test zostanie
  przeprojektowany.

Odłożone: Paweł explicit "nie wiem co z tym zrobić, decyduj sam" — CC
naprawił tylko klasy mechaniczne/pewne tego dnia, resztę zostawił do
realnej analizy przy innej okazji, nie w pośpiechu.

---
