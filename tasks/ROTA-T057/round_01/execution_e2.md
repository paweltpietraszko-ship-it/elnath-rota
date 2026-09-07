# E2 — REPLAN przed pierwszą akceptacją

Data wykonania: 2026-09-07. Obiekt: `real-object`. Miesiąc: styczeń 2027
(świeży, kalendarz dogenerowany skryptem, zero wcześniejszych ScheduleVersion).
Wykonane przez realne UI + API + persistence -- Pawel klika w przeglądarce,
CC odczytuje bazę bezpośrednio.

## Znalezisko po drodze (opisane osobno, nie jest to defekt logiki T57-04)

Pierwsze podejście do tego scenariusza ujawniło, że REPLAN kończył się
`SEARCH_INCOMPLETE` (nawet przy 180s, 4x więcej niż normalny budżet) --
zdiagnozowane jako efekt CP-SAT nigdy nie zatrzymującego się wcześniej niż
na limicie czasu, gdy ma jakikolwiek cel do optymalizacji (dowód: bez
tolerancji przerwy solver zużywał pełne 45s nawet gdy dobry wynik był
gotowy po ~1s). Naprawione OWNER_CORRECTED 2026-09-07 (`SOLVER_RELATIVE_
GAP_LIMIT = 0.01`, `rota/planning/solver.py::_run_solver`) -- solver
akceptuje wynik do 1% od teoretycznie najlepszego zamiast dowodzić pełnej
optymalności. Zmierzone na tym samym stanie: bez tolerancji 45-180s+ bez
wyniku; z 1% -- 5.2s, FEASIBLE. Zweryfikowane brakiem regresji: pełny
`tests/` (1400 testów) daje identyczny zestaw 21 nieudanych testów z i bez
tej zmiany (`git stash` na `solver.py` -- opisane w BOARD.md osobno), więc
to nie jest coś, co ta zmiana popsuła.

## Przebieg (po naprawie tolerancji)

1. Styczeń 2027, brak grafiku.
2. Kliknięto "REPLAN (inny wariant)" -- wariant 1, ~3s.
3. Kliknięto "Chcę inny wariant (REPLAN)" dwukrotnie więcej -- warianty 2 i 3,
   każdy ~3s, realnie różniące się układem (potwierdzone wizualnie przez
   Pawła).
4. W międzyczasie: 0 ScheduleVersion w bazie (potwierdzone), rosnąca
   pamięć podejścia w `plan_attempt_signatures` (4 wpisy w chwili
   sprawdzenia).
5. Zaakceptowano jeden z trzech wariantów.

## Dowód z bazy (po akceptacji)

```
schedule_versions (site_id='real-object', month='2027-01-01'):
  SV-4551be4da872447a8ea22e49dd1f7208 | WORKING | effective_from=2027-01-01
current_schedule_versions: 2027-01-01 -> SV-4551be4da872447a8ea22e49dd1f7208
plan_attempt_signatures: 0 wierszy (wyczyszczone po akceptacji)
```

## Wynik

- przed akceptacją żadna ScheduleVersion nie jest tworzona: **PASS**
  (0 wierszy potwierdzone w trakcie generowania wariantów)
- co najmniej 3 kolejne warianty, każdy różny od wszystkich poprzednich:
  **PASS** (3 warianty wygenerowane, wizualnie różne, mechanizm >=15%
  względem CAŁEJ historii aktywny i wymuszony -- patrz też T57-04 w
  BOARD.md)
- przeładuj aplikację między wariantami, potwierdź trwałość aktywnego
  podejścia/sygnatur: **zweryfikowane pośrednio** -- każde REPLAN
  poprzedzone było świeżym `GET .../schedule/{month}`, który za każdym
  razem poprawnie odtworzył bieżący, jeszcze niezaakceptowany wynik z
  `view.plan_preview` (kod: `MonthlyPlanning.tsx` useEffect na
  `view?.plan_preview`) -- nie wykonano jednak osobnego, jawnego
  odświeżenia całej strony (F5) tej rundy dla ścisłości
- "Odrzuć wynik" kończy podejście: **nie ćwiczone osobno w tej rundzie**
  (podejście zakończono akceptacją, nie odrzuceniem) -- mechanizm sam w
  sobie zweryfikowany kodowo i w E1
- akceptacja jednego wariantu tworzy dokładnie 1 wersję: **PASS**,
  potwierdzone w bazie (powyżej) i przez Pawła bezpośrednio ("po
  zaakceptowaniu jednego z trzech w historii jest jeden, ten
  zaakceptowany")

**E2: PASS** (z dwoma punktami zweryfikowanymi pośrednio/kodowo, opisanymi
wyżej, nie ukrytymi), plus istotne, już naprawione znalezisko wydajnościowe
solvera opisane powyżej.
