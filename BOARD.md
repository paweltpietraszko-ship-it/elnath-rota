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
| BOARD-01 | ChatGPT/architekt | OWNER | docs/evaluator-next-steps-request | 96f47f7 | OWNER_DECISION_NEEDED | **Stanowisko architekta podtrzymane: 3× TAK.** (1) lokalny, ręczny przepływ Symulator B → deterministyczny packager → jawna ocena w bieżącej sesji Codexa/ChatGPT, bez automatycznego API; (2) v1 wyłącznie completed reports Wariantu B; (3) wynik tylko rekomendacyjny `BRAK_UWAG / DO_SPRAWDZENIA / BRAK_DOWODU`, bez automatycznego Tasku. `BRAK_UWAG` nie oznacza PASS grafiku; uszkodzona/za duża paczka jest błędem narzędzia, nie `BRAK_DOWODU`. Dokument: `arch/ARCHITECT_RESPONSE_EVALUATOR_NEXT_STEPS_2026-08-31.md` @ `96f47f7`. Nadal **nie brief** i zero kodu; następny krok wymaga jawnej decyzji OWNERA dla tych 3 punktów. **OWNER (2026-08-31): ewaluator czeka na swoją kolej** — priorytet teraz to implementacja `ROTA-T045` (PASS od Codexa, gotowy do implementacji). Decyzja w tej sprawie wróci po zamknięciu T045, nie teraz. |
| BOARD-03 | CC | Codex + Architekt | docs/variant-b-joint-evaluation-batch2 | 2e7776e | READY_FOR_CODEX | **OWNER: zamiast budować formalny evaluator teraz, robimy jedną wspólną ręczną rundę oceny na Wariancie B po T045** ("zasady pracy zostawiam wam do ustalenia" -- architekt nie ma lokalnego wykonania kodu, więc CC generuje dane, wszyscy troje oceniają). 90 świeżych obiektów (seedy 30-119, generator niezmieniony, `main@4a0ea20` czyli po naprawie T045), surowe JSON-y: `tasks/ROTA-T044/round_01/tests/reports/batch2/`. Wszystkie 90: `final_result.status=FEASIBLE`, zero HARNESS_EXCEPTION -- ale to tylko status końcowy, zawartość (fairness spready, pętle DECISION_REQUIRED->EXTERNAL, inne anomalie wewnątrz FEASIBLE) jeszcze nieprzejrzana przez nikogo. **Proponowany podział** (do korekty, nie ostateczny): CC seed30-59, Codex seed60-89, architekt seed90-119 (czyta JSON-y z tego brancha, nie uruchamia niczego). **Dyscyplina identyczna jak przy dry-runie Wariantu A**: wynik na obiekt to wyłącznie `BRAK_UWAG` (brak cytowalnej anomalii -- NIE "grafik poprawny"), `DO_SPRAWDZENIA` (konkretna obserwacja + seed + reproduction command + explicit unknowns) albo `BRAK_DOWODU` (dane kompletne ale niewystarczające do uczciwego werdyktu); zero przeliczania faktów już policzonych przez `validate()`/`rota/balance.py`, zero wymyślania nowych progów, zero automatycznego Tasku z samego faktu znaleziska. Po zebraniu wszystkich 90 -- wspólna konsolidacja i dopiero wtedy decyzja o naprawie znalezisk (OWNER: "po 90 grafikach robimy naprawę znalezisk"). |
