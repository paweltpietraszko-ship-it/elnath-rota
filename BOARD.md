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
| ROTA-T056 | Codex | CC | `task/ROTA-T056` | `41e9208` (audyt frontendu), raport `91ec7aa` | CODEX_REPORTED | **FAIL — jeden wąski blocker `end_next_day` w frontendzie.** W prawdziwym Chromium `Europe/Warsaw`, przez realne Vite+FastAPI, wybór N6=20:00–06:00 następnego dnia wysyła `2026-08-02T20:00:00`–`2026-08-02T06:00:00`, więc backend słusznie zwraca 500 „end must be after start”. Przyczyną jest dodanie 86400000 do lokalnej północy i następnie `toISOString()`, które konwertuje przez UTC i gubi następny dzień. D6 same-day przeszedł 200; zapis/odczyt per miesiąc, usuwanie, walidacja kodu, filtrowanie D/N oraz wygląd 1600x1000 i 1280x720 przeszły. Build PASS; targetowane backend tests 22 PASS. Poprawić wyłącznie wyznaczanie następnej daty w `applyExtraCode`, bez zmian backendu/solvera. Pełny raport: `tasks/ROTA-T056/round_01/tests/tests_r11.txt` na commit `91ec7aa`. Analogiczny istniejący wzorzec S1 jest jawnie zapisany jako nieblokująca obserwacja poza T056, nie jako wymaganie tej poprawki. |
