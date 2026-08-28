# AUDIT-1 — OWNER CORRECTION: NIEMIARODAJNE BENCHMARKI

**Data:** 2026-08-28  
**Status:** obowiązuje przy wykonaniu AUDIT-1  
**Źródło:** bezpośrednia korekta właściciela po Code Review R5

## Rozstrzygnięcie

Nie uruchamiać w AUDIT-1:

- `benchmarks.rota_stress`;
- `benchmarks.real_object`.

Oba narzędzia zostały wcześniej ocenione jako niemiarodajne dla realnego
obiektu: mogą zwiększać załogę ponad liczbę wynikającą z zapotrzebowania i w
ten sposób ułatwiać solverowi wynik. Ponowne wykonanie nie tworzy wartościowego
baseline'u; zużywa czas i może wyglądać jak dowód działania produktu.

## Dopuszczony przebieg generatywny

Jedynym dopuszczonym narzędziem tego rodzaju jest Symulator Koordynatora
T038/T039, ponieważ odtwarza produkcyjne wejścia i reaguje na rzeczywiste
statusy PLAN/REPLAN. Nadal nie jest oracle poprawności: jego raport podlega
niezależnej ocenie Codexa, a samo „pytest PASS” oznacza tylko brak wyjątku/5xx.

Symulator ma zostać uruchomiony dokładnie raz. Pełny pytest pomija jego moduł,
aby nie wykonać kosztownego przebiegu drugi raz i nie nadpisać historycznego
raportu T038.

## Brak rozszerzenia produktu

Ta korekta usuwa dwa wadliwe pomiary i nie dodaje nowego wymagania produktu,
generatora ani benchmarku. Pionowe scenariusze Warstwy B pozostają głównym
dowodem działania aplikacji.
