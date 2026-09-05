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
| ROTA-T056 | Codex | Owner | `main` (brief only; implementation HOLD) | `e4260555645c5c00a3829bacf28bcc1233422f47` (audited brief) | OWNER_DECISION_NEEDED | **PREIMPLEMENTATION AUDIT R1 — bez PASS/FAIL.** Raport: `tasks/ROTA-T056/round_01/tests/tests_r1.txt`. Dwie decyzje produktowe: (1) zachowanie eksportu, gdy liczba/długość dodatkowych kodów nie mieści się w zaakceptowanym PDF; rekomendacja: fail-closed z polskim komunikatem i korektą konfiguracji, alternatywa: dodatkowe strony legendy; (2) zachowanie przy kolizji podpisu utworzonej w dowolnej kolejności przez zapis extra code albo późniejszy zapis globalnych standardowych interwałów; rekomendacja: odrzucać drugi zapis na obu owning boundaries, zachować poprzednie dane i wskazać kolizję, alternatywa: dopuścić zapis i blokować eksport miesiąca. Korekty techniczne briefu: naprawić `frontend/src/Room.tsx` na `frontend/src/screens/Room.tsx`, dodać `frontend/src/screens/ControlPanel.tsx`; jawnie wpisać testy i miejsce dowodu REAL PDF; podać wąski plan spełnienia istniejącego size gate (`db.py` 635>600, `schedule_export.py` 684>600, `_apply_24h_periods` 53>50); objąć invariantem oba write paths oraz read/export fail-closed; użyć istniejącego unified action history; dodać `WHERE_MAP: REQUIRED`. Cztery wąskie testy migracji są czerwone już na bazie przez zastane literalne oczekiwania wersji schematu — sklasyfikować jako stale/source-shape, nie regresję T056. Kod produktu pozostaje wstrzymany do decyzji OWNERA, jednej korekty briefu i re-audytu exact SHA. |
