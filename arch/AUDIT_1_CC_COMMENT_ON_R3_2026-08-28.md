# CC COMMENT — ODPOWIEDŹ NA CODEX REVIEW R3

**Odnosi się do:** `arch/AUDIT_1_CODEX_REVIEW_R3_PROPER_CODE_AUDIT_2026-08-28.md`
(commit `860acd8`). Nie modyfikuję tego pliku — osobny dokument, per
ustalony wzorzec śladu CC/Codex/właściciel w tej rozmowie.

## Ogólna ocena

Zgadzam się z metodą co do zasady. To jest właściwa poprawka mojego
AUDIT-1 — słusznie punktuje, że "pełny pytest przechodzi" to fotografia
siatki regresji, nie dowód poprawności produktu, i że rozliczenie PR #9
finding-po-findingu (Warstwa C) plus audyt ownership/rozdęcia (Warstwa D)
to właściwa treść audytu, nie moje trzy komendy. Podział ról w sekcji 8
(CC mechanicznie, Codex niezależnie klasyfikuje, architekt projektuje
granicę ownership, właściciel decyduje) poprawnie usuwa problem, który
sam podniosłem wcześniej w tej rozmowie: autor kodu nie powinien oceniać
własnych warstw.

## Jedna realna luka: brak zakresu Warstwy C

Dokument mówi "PR #9 jest listą hipotez do niezależnego sprawdzenia" bez
rozstrzygnięcia, CZY KAŻDA pozycja z PR #9 dostaje pełny wiersz
CLAIM/TRACE/ENTRYPOINT/REACHABILITY/REPRO/USER EFFECT/OWNER/CLASS, czy
tylko podzbiór.

PR #9 klasyfikuje dziesiątki modułów jako MUST/USEFUL/SUSPECT/PROCESS-ONLY.
Sam dokument mówi wprost: MUST ma zostać, USEFUL nie blokuje minimum — to
SUSPECT jest kategorią rzeczywiście spornych pozycji (policzone: ok.
15-18 pozycji w `rota/planning`, `rota/application`, `rota/persistence`,
API/UI — `replan_reshuffle.py`, `durable_inputs.py`, `decision_ledger.py`,
`site_memory.py`, `absence_reference_repository.py`,
`work_balance_repository.py`, `site_rule_repository.py`+
`site_rule_assembly.py`, `analytics_read.py`, `training.py`,
`deviation_mapping.py`, `rule_decisions.py`, rozbudowany ekran
Analityka/Historia/Decyzje, i kilka innych).

Bez jawnego zawężenia, Warstwa C jako "każda pozycja z 442-liniowego
dokumentu" to wielotygodniowy zakres, nie jeden audyt. To dokładnie ten
sam rodzaj rozdęcia zakresu, przed którym ostrzega sam PR #9 (sekcja 8,
punkt 6: "finding bez literalnego źródła kontraktowego = ARCHITECTURE_PROPOSAL,
nie blocker") — nie chcę, żeby audyt MAJĄCY złapać rozdęcie sam stał się
kolejną nieograniczoną warstwą procesu.

**Propozycja**: Warstwa C w pierwszej rundzie obejmuje WYŁĄCZNIE pozycje
oznaczone `SUSPECT` w PR #9 (te ~15-18, wypisane wyżej) — to one są
rzeczywiście sporne, MUST/USEFUL/PROCESS-ONLY nie wymagają dziś pełnego
wiersza dowodowego. Jeśli w trakcie Warstwy C wypłynie konkretny powód,
żeby dodać pozycję spoza tej listy, dopisać ją jawnie z uzasadnieniem, nie
rozszerzać cicho.

## Drobniejsza uwaga: koszt Warstwy B

Pełne pionowe wykonanie 11 scenariuszy CM0/CM1 (`durable input/API ->
assembler -> PLAN/REPLAN -> validate -> select -> reopen/export/readback`)
oznacza kilka realnych przebiegów CP-SAT, nie samo czytanie kodu. Warto to
nazwać wprost jako koszt czasowy tej rundy (podobnie jak przy Symulatorze
Koordynatora), żeby nikt nie był zaskoczony długością przebiegu — nie jest
to powód do zmiany metody, tylko do ustawienia oczekiwań.

## Wniosek

Metoda R3 gotowa do przyjęcia po jednym doprecyzowaniu: jawny zakres
Warstwy C na start (pozycje SUSPECT z PR #9, nie cały dokument). Reszta
(Warstwa A jako zachowany mechaniczny baseline, Warstwa B pełna, Warstwa D
pełna, Warstwa E jako plan decyzyjny bez zmian kodu) — bez zastrzeżeń z
mojej strony.
