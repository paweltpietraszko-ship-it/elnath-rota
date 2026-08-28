# CODEX REVIEW R5 — AUDIT-1 GOTOWY DO WYKONANIA

**Reviewed branch:** `docs/audit-1-baseline-brief`  
**Reviewed exact SHA:** `f19eaea1db1a78153db0e0d58dd1409f3409d11d`  
**BASE_SHA:** `d445ee64a0e634c4ca23c2fcc9f6a50b6503d22b`  
**PR #9 source:** `f2eba6ce97d19d03fbef3c7bd4fe3c417ff55a05`  
**Reviewer:** Codex, independent tester/auditor  
**Status:** `PASS — READY_FOR_EXECUTION`

## Zakres tej recenzji

To jest PASS skonsolidowanego briefu wykonawczego, nie werdykt o poprawności
produktu. Sprawdzono konsolidację ustaleń R1-R4 i istnienie wskazanych SHA.
Nie uruchamiano jeszcze właściwego AUDIT-1.

Brief poprawnie:

- przypina mechaniczny baseline do istniejącego `BASE_SHA` sprzed T040;
- oddziela surowy wynik Warstwy A od werdyktu o produkcie;
- wymaga 11 rzeczywistych pionowych przebiegów w Warstwie B;
- zamyka Warstwę C na czterech potwierdzonych incydentach C-01..C-04;
- przenosi pozostałe pozycje SUSPECT z przypiętego źródła PR #9 do
  strukturalnego remanentu Warstwy D;
- pozostawia Warstwę E jako późniejszy plan decyzyjny, bez implementacji;
- zakazuje napraw, nowych testów i refaktoryzacji podczas zbierania dowodów.

## Warunki wykonania

1. Warstwy A-D mają być wykonane na dokładnie wskazanym `BASE_SHA`, nie na
   aktualnym HEAD gałęzi ani na kodzie po T040.
2. Wynik scenariusza 11 na tym baseline ma zostać zapisany zgodnie z faktem:
   obecne `DECISION_REQUIRED` jest dowodem baseline'u, a nie powodem do
   poprawienia kodu w trakcie audytu.
3. Nowy błąd znaleziony w Warstwie D może wejść do tabeli incydentów dopiero
   z własnym TRACE/OWNERSHIP/REPRO. Sama etykieta SUSPECT nie jest defektem.
4. Wykonanie kończy się artefaktami A-D. Jakiekolwiek cięcie, naprawa albo
   realizacja Warstwy E wymaga osobnej decyzji i osobnego zadania.

Nie ma potrzeby kolejnej rundy projektowania briefu przed rozpoczęciem
zbierania dowodów.
