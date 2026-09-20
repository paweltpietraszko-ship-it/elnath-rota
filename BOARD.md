# BOARD.md — kolejka przekazań Architekt ↔ Codex ↔ CC

Każda nowa instancja Architekta przed podjęciem Tasku musi przeczytać w całości
`ARCHITECT_START_HERE.md`. Każda nowa instancja Codexa postępuje zgodnie z
`AGENTS.md` i `CODEX_START_HERE.md`.

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
| ROTA-EXCEL-UI-PANEL | CC | Antigravity | `task/ROTA-EXCEL-UI-PANEL` | `7bd671b` (on top of audited `0ac8933`, PASS `a654c59`) | READY_FOR_CODEX | Owner instrukcja po PASS, przed merge: dodać w panelu przycisk "Instrukcja instalacji" udostępniający `excel/INSTALL.md` w czytelnej formie, nie jako surowy plik do pobrania. Dodane: `GET /api/excel/install-guide` (cookie auth) zwraca treść pliku; frontend renderuje ją małym, własnym parserem markdown (nagłówki, listy, **bold**, `code`) w nowym scrollowalnym modalu -- bez dodawania biblioteki. Bug znaleziony i naprawiony podczas własnej weryfikacji wizualnej: pierwsza wersja parsera kończyła listę na każdej linii bez markera, więc zawijane (wielolinijkowe) pozycje list -- częste w tym dokumencie -- rozbijały listę na kilka, każda zaczynająca numerację od 1; naprawione przez zwijanie linii-kontynuacji do bieżącej pozycji/akapitu. Zweryfikowane: `tsc -b` czyste, `ruff check` czyste, backend end-to-end (`login → /api/excel/install-guide` zwraca pełną treść), i tym razem PEŁNA weryfikacja wizualna w przeglądarce (rozszerzenie Chrome wróciło online) -- cały dokument, wszystkie 6 sekcji, przewinięte i sprawdzone, numeracja list poprawna po fixie. Jedno świadome uproszczenie: zagnieżdżona lista pod krokiem 3 sekcji 4 (przypisania makr do przycisków) renderuje się jako spłaszczony tekst ciągły zamiast wciętej podlisty -- czytelne, ale nie idealne wizualnie; nie budowałem pełnej obsługi zagnieżdżonych list dla tego jednego miejsca. |
