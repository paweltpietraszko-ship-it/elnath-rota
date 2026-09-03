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
| BOARD-09 | Codex | CC | task/ROTA-T050 | 2e1306a | CODEX_REPORTED | Preimplementation audit exact `b8434a1` — **FAIL**, jeden blocker. `openSite` ma 16 współdzielonych wywołań, nie 7. `diagnostics.spec.ts:200-201` nie wykonuje własnej nawigacji i po proponowanej zmianie nadal kończy timeoutem na `roster-add-open`; potwierdzone jednym celowanym testem przeglądarkowym. T50-01 potwierdzone bez uwag. Raport: `tasks/ROTA-T050/round_01/tests/tests_r1.txt`. |
| BOARD-10 | Codex | Owner | task/ROTA-T051 | 7e1751b | OWNER_DECISION_NEEDED | OWNER_EXPLANATION_GATE dla exact `1e243f6`: trzeba zatwierdzić dokładny wygląd skrótu — 10 znaków, polskie etykiety oraz pozostawienie pełnego `SV-...` na PDF. Dodatkowo T51-06 przeczy sekcji 4 w sprawie wyniku `_provenance_text` i wymaga mechanicznej korekty. Bez werdyktu PASS/FAIL do decyzji OWNERA. Raport: `tasks/ROTA-T051/round_01/tests/tests_r1.txt`. |
