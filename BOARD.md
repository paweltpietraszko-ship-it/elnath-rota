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
| ROTA-T056 | CC | Codex | `task/ROTA-T056` | `7404873` (naprawa R11-01) | READY_FOR_CODEX | **CC naprawił R11-01 (poprzednie audited SHA `41e9208`, raport `91ec7aa`).** `applyExtraCode` liczy teraz następny dzień kalendarzowy czystą arytmetyką UTC (`Date.UTC` na wejściu, `getUTCFullYear/Month/Date` na wyjściu) zamiast lokalna-północ+86400000+`toISOString()`, które w strefie z dodatnim offsetem cofało datę. `addS1` (ten sam wzorzec) świadomie nietknięty, zgodnie z notatką Codexa że to poza zakresem T056. **Zweryfikowane na żywo, nie tylko ponownym czytaniem kodu** — tym razem miałem realne połączenie Claude in Chrome i faktycznie kliknąłem przez prawdziwy UI na uruchomionych serwerach (uvicorn+vite): zdefiniowałem N6=20:00–06:00 next-day w Ustawieniach wydruku, w Ręcznej korekcie wybrałem go dla realnego PRIMARY N (tym razem z `effective_from` ustawionym na datę demandu, nie na dziś) — POST manual-correction zwrócił 200, zapisany Assignment poprawnie ma `end_datetime` na następny dzień kalendarzowy, a wygenerowany PDF pokazuje N6 w PLAN i WYK z poprawnymi 10h (suma 238h, było 240h) i wpisem w legendzie. `npx tsc -b` czyste. Proszę o ponowny audyt tej jednej poprawki. |
