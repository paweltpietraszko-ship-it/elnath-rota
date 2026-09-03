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
| BOARD-09 | Codex | CC | task/ROTA-T050 | 36c4129 | CODEX_REPORTED | Audyt implementacji exact `4202856`: **PASS**. 6/6 testów Pythona, diagnostics privacy canary PASS, shift-catalog PASS; monthly-planning potwierdził poprawny seam `openSite`, a późniejszy stary `status: WORKING` pozostaje osobnym backlogiem #15. Dodatkowy licznik LOCAL jest zgodny z T041 i nie zmienia produktu. Raport: `tasks/ROTA-T050/round_01/tests/tests_r3.txt`. |
| BOARD-10 | Codex | CC | task/ROTA-T051 | 2cdc2a8 | CODEX_REPORTED | Audyt implementacji exact `d7e3a18`: **FAIL**, jeden wąski punkt. Widoczny PDF i ekran są poprawne, `document_revision` pozostaje pełne, ale `_provenance_text` zasila także `ExportReady.schedule_provenance`, więc API dostało skrócony tekst zamiast pełnej, niezmienionej technicznej wartości wymaganej przez brief. Niezależny reproduktor zachowany; poprawić wyłącznie rozdzielenie pełnej wartości API od skróconej prezentacji. Raport: `tasks/ROTA-T051/round_01/tests/tests_r4.txt`. |
