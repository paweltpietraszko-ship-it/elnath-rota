# FINDING 2026-09-24 — 34 stabilne porażki testów na `main`, niezdiagnozowane

STATUS: pomiar, **ZDIAGNOZOWANY PÓŹNIEJ TEGO SAMEGO DNIA** — diagnoza jest w
`ODLOZONE.md`, sekcja „2026-09-24 34 stabilne porażki testów na main". Inna
sesja zrobiła bisect po commitach i eksperymenty w tymczasowych worktree:
**żadna z 34 nie jest błędem produktu — to przestarzałe testy.** Naprawa
odłożona do jednego bloku po opiniach testera.

Ta notatka zostaje jako zapis pomiaru i pułapki z interpreterem. Diagnozy tu
nie powtarzam — dwie kopie jednego ustalenia z czasem zaczną mówić co innego.
Obowiązuje `ODLOZONE.md`.

DATA: bez związku z danymi osobowymi; pomiar na kodzie, patrz
`arch/DATA_STATUS.md`.

## Co zmierzono

Pełna suita na `main`, interpreter z `.venv`, dwa niezależne przebiegi:

```
.venv\Scripts\python.exe -m pytest tests -q

przebieg 1:  34 failed, 1465 passed, 1 skipped   (3 min 50 s)
przebieg 2:  34 failed, 1465 passed, 1 skipped   (4 min 12 s)
```

**Listy padających testów są identyczne — 34 wspólne, 0 różnic.**

To wyklucza niedeterminizm solvera jako wyjaśnienie. Gdyby chodziło o losowy
wybór CP-SAT przy remisie — zjawisko udokumentowane w
`arch/FINDING_2026-09-21b_SATURDAY_CONCENTRATION_CONFIRMED_ON_BOLF_SITE.md`,
gdzie trzy uruchomienia PLAN na niezmienionych danych dały różne rozkłady —
listy rozjechałyby się choćby o jeden test.

## Pułapka pomiarowa, którą warto zapisać

Pierwszy pomiar dał **53 porażki**. Był błędny: uruchomiłem suitę globalnym
Pythonem zamiast `.venv`, a w tamtym interpreterze nie ma `sqlalchemy`.
Dziewiętnaście „porażek" to były podprocesy przewracające się na braku
zależności.

Wniosek dla każdego, kto będzie to powtarzał: **`python -m pytest` bez
aktywowanego środowiska produkuje fałszywe porażki.** Komenda musi zaczynać
się od `.venv\Scripts\python.exe`.

## Rozkład

34 porażki w 22 plikach, po jednej do sześciu — warstwa rozsiana po całości,
nie jeden zepsuty moduł.

| plik | ile |
|---|---|
| `test_t022_planning_integrity.py` | 6 |
| `test_audit_t010_r5_b.py` | 4 |
| `test_t017.py`, `test_t010_day_only_n_exception.py`, `test_manual_audits.py`, `test_audit_t010_r3.py` | po 2 |
| pozostałe 16 plików | po 1 |

## Przykłady powodów, dosłownie

- `assert False` — 8 razy
- `assert not True` — 6 razy
- `assert 'FEASIBLE' != 'FEASIBLE'` — 2 razy: test oczekuje, że plan NIE
  wyjdzie, a wychodzi
- `Failed: DID NOT RAISE CandidateRejected` — odrzucenie, które przestało
  następować
- `assert 'DECISION_REQUIRED' == 'TECHNICAL_ERROR'` — zmieniona klasyfikacja
- `assert 'canonical_site_absence_days' in <źródło schedule_export>` — test
  czyta źródło modułu i nie znajduje w nim symbolu

Kilka z nich siedzi w plikach `test_audit_*`, czyli w testach regresyjnych
pisanych po to, by zamrozić poprawki znalezione przez audytora.

## Czego ta notatka NIE ustalała (rozstrzygnięte w `ODLOZONE.md`)

- czy którakolwiek z tych porażek to regresja funkcjonalna
- czy którakolwiek to test nieaktualny wobec świadomej zmiany produktu
- czy `main` jest sprawny dla użytkownika — nie uruchomiono aplikacji

## Co by to rozstrzygnęło (zrobione — patrz `ODLOZONE.md`)

Dla każdej z 34: znaleźć brief lub decyzję OWNERA, która ustaliła zachowanie
sprawdzane przez ten test, i porównać z tym, co robi kod dziś. Zgodne z
decyzją → test nieaktualny, do aktualizacji. Niezgodne → regresja.

To jest praca na osobne zadanie, nie na przypis.
