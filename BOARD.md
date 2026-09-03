# BOARD.md — kolejka przekazań CC ↔ Codex

Nie czytane automatycznie jak AGENTS.md — trzeba wprost polecić "na początku
czytaj BOARD.md" (patrz AGENTS.md). To jest wyłącznie dziennik przekazania:
kto, co, na jakim SHA, gdzie leży raport. Żadnych ustaleń produktowych,
żadnych decyzji właściciela — te nadal trafiają do brief.md/kontraktu danego
Tasku. PR pozostaje realnym wyzwalaczem pracy; ten plik tylko rejestruje
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
| BOARD-09 | Codex | CC | task/ROTA-T050 | 7b1259b | CODEX_REPORTED | **PASS** preimplementation reaudytu exact `86ddeaf`. R1 zamknięte: 16 wywołań policzone poprawnie, istniejący wzorzec kliknięcia w Panel sterowania naprawia dokładny reproduktor. Wąska próba: privacy canary PASS, shift-catalog PASS, monthly-planning przeszedł cały seam `openSite` i zatrzymał się dopiero na niezależnym starym tekście `status: WORKING` po T048 — sklasyfikowany jako znany test niezgodny z aktualnym PRODUCT_TRUTH, nie regresja T050. Raport: `tasks/ROTA-T050/round_01/tests/tests_r2.txt`. |
| BOARD-10 | Codex | CC | task/ROTA-T051 | 264ffa9 | CODEX_REPORTED | **PASS** preimplementation reaudytu exact `0e2ad16`. OWNER_CORRECTED zastosowane: brak widocznego `SV-...`, człowiek identyfikuje wydruk nazwą obiektu i datą/okresem, pozostaje tylko krótki kod weryfikacyjny; T51-03 i T51-06 są już spójne. Raport: `tasks/ROTA-T051/round_01/tests/tests_r3.txt`. |
