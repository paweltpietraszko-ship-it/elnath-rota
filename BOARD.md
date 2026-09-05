# BOARD.md — kolejka przekazań CC ↔ Codex

Nie czytane automatycznie jak AGENTS.md — trzeba wprost polecić "na początku
czytaj BOARD.md" (patrz AGENTS.md). To jest wyłącznie dziennik przekazania:
kto, co, na jakim SHA, gdzie leży raport. Żadnych ustaleń produktowych,
żadnych decyzji właściciela — te nadal trafiają do brief.md/kontraktu danego
Tasku. PR pozostaje realnym wyzwalzem pracy; ten plik tylko rejestruje
przekazanie, żeby nie trzeba było ręcznie przeklejać wiadomości między CC a
Codexem.

Statusy (dokładnie cztery, nic więcej):

- `READY_FOR_CODEX` — CC skończył, czeka na audyt.
- `CODEX_IN_PROGRESS` — Codex audytuje.
- `CODEX_REPORTED` — raport gotowy pod wskazaną ścieżką.
- `OWNER_DECISION_NEEDED` — audyt utknął na decyzji właściciela.

Nowy wiersz dopisuje autor przekazania; zmianę statusu na kolejny etap
wpisuje ten, kto ten etap kończy. Zamknięty wiersz (merge/decyzja, ostatni
status rozstrzygnięty) usuwa z tego pliku ten, kto go zamyka — pełna
historia i tak zostaje w `git log -p BOARD.md`, więc nic nie ginie, tylko
plik nie rośnie w nieskończoność (2026-08-29, OWNER_CORRECTED: wcześniejsza
wersja tej reguły mówiła "nie kasować wierszy" — celowo zmienione).

| ID | Autor | Odbiorca | Branch | Exact SHA | Status | Wiadomość |
|---|---|---|---|---|---|---|
| ROTA-T056 | Codex | CC | `task/ROTA-T056` | `429e432` (audytowane artefakty), `a9d73ec` (raport R13) | CODEX_REPORTED | **FAIL — Gate A PASS, ale zapisany Gate B nie uruchamia T56-15.** Wszystkie trzy pliki §16 istnieją i commit `429e432` nie zmienia kodu produktu. Optyczny re-check wszystkich stron pokazuje jednak, że strona 4 `real_pdf_gate_b.pdf` nadal zawiera siatkę i pracowników EMP-6–EMP-9, a pod nią zwykłą legendę „Legenda — użyte w tym wydruku oznaczenia...”. Nie jest to deklarowana dedykowana strona wyłącznie na legendę i nie ma nagłówka ścieżki `legend_needs_own_page`: „Legenda — ciąg dalszy...”. PDF jest czytelny i ma komplet 40 wpisów, lecz nie dowodzi wymaganej klasy T56-15/R8-04. `real_pdf_gate_review.md` jest przez to sprzeczny z wydrukiem; dodatkowo myli numery Gate A/B (powinny być T56-14/T56-15, nie T56-13/T56-14). Wąska poprawka: bez zmian produktu zastąpić tylko Gate B artefaktem faktycznie tworzącym dodatkową stronę legendy i skorygować review; Gate A nie wymaga powtórzenia. Raport: `tasks/ROTA-T056/round_01/tests/tests_r13.txt`. |
| ROTA-SOLVER-RHYTHM-VS-TARGET | CC | Architekt | — (brak brancha, brak brief.md) | `17c2657` (finding) | OWNER_DECISION_NEEDED | **Prośba o brief: solver poświęca rytm D/N/W/W i unikanie 3 zmian pod rząd dla precyzji equity w target_hours, nawet gdy target strukturalnie nieosiągalny.** Pełny opis: `arch/FINDING_2026-09-05_SOLVER_RHYTHM_VS_TARGET_PRECISION.md` (main@`17c2657`). Skrót: obiekty mają zwykle nadwyżkę zatrudnienia (bufor na urlopy/L4), więc suma `target_hours` przewyższa realne zapotrzebowanie — część niedoboru jest z góry nieunikniona. Mimo to `add_target_equity_fairness` (`fairness.py:139-168`) dalej wyrównuje procent realizacji między pracownikami z dokładnością co do godziny, kosztem rytmu D/N/W/W i unikania 3 zmian pod rząd (`DN_RHYTHM_REWARD_WEIGHT`/`THIRD_CONSECUTIVE_SHIFT_PENALTY_WEIGHT` = 1, matematycznie zdominowane przez `TARGET_DEVIATION_WEIGHT`+equity, `solver.py:493-514/549-554`, OWNER_CORRECTED 2026-08-25). OWNER: koordynator w realnej pracy **nigdy** nie robi 3 zmian pod rząd — to bliżej HARD niż SOFT. Program już ma na to gotowy mechanizm: `DECISION_REQUIRED` (`engine.py`, dziś używany dla REST-01/LOAD-01/MEMBERSHIP-01), ale "3 zmiany pod rząd" nie jest do niego podłączone. 3 otwarte pytania projektowe w dokumencie (poziom priorytetu dla 3-zmian-pod-rząd vs ogólnego rytmu, czy equity potrzebuje pasma tolerancji, czy to jeden mechanizm czy dwa). CC nie projektuje rozwiązania — dotyka solvera, wymaga architekta. |
