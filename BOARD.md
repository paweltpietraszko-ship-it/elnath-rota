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
| BOARD-01 | CC | Codex/architekt | task/ROTA-T044 | 083d4c6 | READY_FOR_CODEX | Naprawiony ARCH-R1-01 (`ARCHITECT_IMPLEMENTATION_REVIEW_R1.md` FAIL na `e80103d`). Dodany bezwarunkowy, neutralny raw-report path: `_write_completed_report()` wywoływane z `teardown()` dla KAŻDEGO przykładu, który dotarł do PLAN i nie zakończył się już zapisanym failure JSON (nowa flaga `self._failed` zapobiega duplikatowi) -- ten sam komplet danych co snapshot awarii (seed, miesiąc, atoms, kalkulator, roster, absencje, kolejność akcji, historia PLAN/EXTERNAL/select/REPLAN, gotowa komenda), zero oceny solvera. Zapisywane do nowego `tests/**/reports/` (osobno od `failures/**`). Dwa testy celowane: zwykły ukończony przebieg (realne API) i wymuszony `TECHNICAL_ERROR` (monkeypatch) -- oba muszą się zapisać, nieprzeinterpretowane. Zweryfikowane też na realnym przebiegu maszyny stanów: dokładnie 8 plików raportów (= `max_examples`), potwierdzając że mechanizm faktycznie działa, nie tylko w testach celowanych. Wygenerowane pliki raportów NIE są commitowane (efemeryczne dane z przebiegu, nie trwałe znalezisko jak `failures/**`). ARCH-R1-02 (kandydat REPLAN bez ścieżki select) świadomie pominięty -- architekt oznaczył NON_BLOCKING i prosił nie mieszać bez osobnej decyzji OWNERA. Zweryfikowane: ruff czyste, 60/60 testów niestanowych, maszyna stanów PASS (~333s, nadal poniżej ~750s). Proszę o kolejny niezależny audyt/ocenę architekta. |