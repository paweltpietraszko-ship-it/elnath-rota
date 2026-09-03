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
| BOARD-09 | CC | Codex | task/ROTA-T050 | b8434a1 | READY_FOR_CODEX | Brief `ROTA-T050` gotowy do preimplementation audytu — dwa niezależne, martwe testy sprawdzające dawno nieaktualny tekst, znalezione przypadkiem przy audytach T048/T049 (backlog CC, pozycje 13-14), zero zmiany produktu. (1) `tests/test_t009_open_and_assembler.py:92` filtruje po angielskim `"omitted from WorkBalance context"`, którego `assembler.py` już dawno nie zwraca (przetłumaczone przy T041) — zamiana na stabilny fragment aktualnego polskiego tekstu. (2) `frontend/e2e/helpers.ts::openSite` czeka na nagłówek „Panel sterowania”, choć obiekt otwiera się domyślnie na „Przegląd”, ekran bez żadnego nagłówka `role="heading"` — zamiana na ten sam idiom, którego `createSite` już używa (czekanie na okruszek z nazwą obiektu). Sprawdzone: wszystkie 7 wywołań `openSite` robią własną dalszą nawigację zaraz po nim, żadne nie zakłada ukrytego efektu starego warunku. Oba znaleziska potwierdzone jako już czerwone/martwe na odpowiednich kontraktach PASS T048/T049, przed ich implementacją. Dokument: `tasks/ROTA-T050/brief.md`. |
