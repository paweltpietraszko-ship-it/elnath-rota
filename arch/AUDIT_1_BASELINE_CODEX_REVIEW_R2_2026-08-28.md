# CODEX REVIEW R2 — AUDIT-1 BASELINE BRIEF

**Reviewed branch:** `docs/audit-1-baseline-brief`  
**Reviewed exact SHA:** `23e4a195fae9e08185f8f578898a3444bddc00f9`  
**Reviewer:** Codex, independent tester/auditor  
**Status:** `WYMAGA_KOREKTY`

## Rozliczenie uwag rundy 1

Trzy wymagane korekty zostały zastosowane prawidłowo:

1. CC w punkcie 4 wyłącznie wskazuje kandydatów `plik::nazwa_testu` albo
   `BRAK KANDYDATA`; nie klasyfikuje pokrycia i nie pisze testów.
2. Scenariusz H24 został zawężony do dokładnego CM0 i nie twierdzi już, że
   każdy DECISION_REQUIRED dla H24 jest błędny.
3. Ustalono osobne ścieżki surowych artefaktów, a PASS/FAIL benchmarku jest
   jawnie wynikiem narzędzia, nie werdyktem zgodności produktu.

## A1-R2-01 — nieistniejący BASE_SHA

Brief nadal nie może zostać wykonany, ponieważ jego deklarowany exact
`BASE_SHA` nie istnieje w repozytorium:

`d445ee6244e4e43f504ef44b9b5a290f05a21b7`

Niezależna kontrola `git cat-file -t` zwraca dla tej wartości
`Not a valid object name`.

Rzeczywisty commit `main` o skrócie `d445ee6` to:

`d445ee64a0e634c4ca23c2fcc9f6a50b6503d22b`

z opisem `Merge: ROTA-T039 heterogeneous shift catalogs in Symulator
Koordynatora`.

AUDIT-1 ma być baseline'em na dokładnym SHA, dlatego CC nie może sam
domyślać się poprawnego obiektu podczas wykonania. Wymagana jest wyłącznie
mechaniczna korekta pełnej wartości `BASE_SHA`; pozostały zakres jest
zaakceptowany bez kolejnych zmian.

## PREIMPLEMENTATION_REDUCTION_GATE

Po korekcie SHA pozostaje konieczne i wystarczające:

- pełny pytest;
- oba istniejące benchmarki;
- mechaniczna lista kandydatów pokrycia dla 11 scenariuszy;
- ustalone surowe artefakty i jeden raport zbiorczy;
- zero napraw, nowych testów i interpretacji CC.

Werdykt dla exact SHA briefu `23e4a195fae9e08185f8f578898a3444bddc00f9`:
`WYMAGA_KOREKTY` wyłącznie z powodu A1-R2-01.
