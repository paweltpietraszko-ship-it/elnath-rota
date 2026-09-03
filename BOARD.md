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
| BOARD-07 | CC | Codex | task/ROTA-T048 | 105efdc | READY_FOR_CODEX | R2: zastosowano OWNERA decyzje z audytu R1 (`tests_r1.txt` @ `aec6f7d`). OWNER_DECISION_NEEDED 1 (historia wersji): zamiast usuwać `version_id` bez zamiennika, każdy wiersz dostaje `SCHEDULE_STATUS_LABEL[status]` + `formatDateTime(created_at)` (dane już w API, zero nowego odczytu) — dwie wersje o tym samym statusie są teraz rozróżnialne po dacie utworzenia. OWNER_DECISION_NEEDED 2 (blokujące zmiany): OWNER odrzucił rozszerzanie `BlockingDemand`/`DecisionRequiredPayloadOut` o D/N+liczbę osób (to zmiana publicznego kontraktu, osobny Task z architektem gdyby kiedyś potrzebny) — zamiast tego pozycje na liście numerowane w kolejności wyświetlania („Zmiana {i+1}: {zakres dat}”, nie „Poprawka” — kolizja z istniejącą nazwą funkcji ręcznej korekty, OWNER potwierdził). UNAUTHORIZED/SPRZECZNOŚĆ 1: carry-in warning poprawiony na neutralne „bilans godzin z wcześniejszej części kwartału przyjęto jako 0” — bez `target_hours` i bez błędnego „nadgodziny” (bilans bywa ujemny, zamrożony kontrakt analityki tego zakazuje). TECHNICAL_ONLY: `renderStateValue` w `History.tsx` dostaje drugi parametr `key`, tłumaczenie `ORDINARY`→`standardowy` zawężone do klucza `planning_regime` — wolny tekst koordynatora zawierający to słowo już nie zostanie fałszywie podmieniony. Reszta briefu (sekcje 1-3, 8-9, macierz T48-01…04/08) bez zmian względem R1. Proszę o wąski reaudyt tylko tych czterech punktów. |
