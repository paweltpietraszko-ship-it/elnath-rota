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
| BOARD-07 | Codex | CC | task/ROTA-T048 | c77253e | CODEX_REPORTED | `PASS`. Wąski reaudyt objął wyłącznie R3-01. `timeStyle: "medium"` rozróżnia `10:00:01` i `10:00:59`; TypeScript oraz build produkcyjny przeszły, `git diff --check` czysty. Nie powtarzano pozostałych testów T048 ani pełnej suity. Raport: `tasks/ROTA-T048/round_01/tests/tests_r4.txt` na `task/ROTA-T048@e1ff417`. |
| BOARD-08 | Codex | CC | task/ROTA-T049 | b423c72 | CODEX_REPORTED | `WYMAGA WĄSKIEJ KOREKTY PRZED IMPLEMENTACJĄ`. Kierunek OWNERA jest jasny; architekt i nowa decyzja nie są potrzebne. Brief pomija dwa żywe, bezpośrednie odwołania do usuwanego pola w `frontend/e2e/diagnostics.spec.ts:57,96`; musi też jawnie zastąpić zamrożone trzy-pola T021 (`arch/T021_spec.md:401`, `tasks/ROTA-T021/brief.md:167,177`). Technicznie należy poprawić nieprawdziwe zdanie o historii: `_profile_state` nie serializuje `display_name`, a `History.tsx:64` mapuje `profile_id`. Bez testów — audyt kontraktu. Raport: `tasks/ROTA-T049/round_01/tests/tests_r1.txt` na `task/ROTA-T049@081b3a7`. |
