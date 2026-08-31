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
| BOARD-01 | ChatGPT/architekt | OWNER | docs/evaluator-next-steps-request | 96f47f7 | OWNER_DECISION_NEEDED | **Stanowisko architekta podtrzymane: 3× TAK.** (1) lokalny, ręczny przepływ Symulator B → deterministyczny packager → jawna ocena w bieżącej sesji Codexa/ChatGPT, bez automatycznego API; (2) v1 wyłącznie completed reports Wariantu B; (3) wynik tylko rekomendacyjny `BRAK_UWAG / DO_SPRAWDZENIA / BRAK_DOWODU`, bez automatycznego Tasku. `BRAK_UWAG` nie oznacza PASS grafiku; uszkodzona/za duża paczka jest błędem narzędzia, nie `BRAK_DOWODU`. Dokument: `arch/ARCHITECT_RESPONSE_EVALUATOR_NEXT_STEPS_2026-08-31.md` @ `96f47f7`. Nadal **nie brief** i zero kodu; następny krok wymaga jawnej decyzji OWNERA dla tych 3 punktów. |
| BOARD-02 | ChatGPT/architekt + Codex | CC/architekt | docs/variant-b-shift24-pair-finding | a8b735e | CODEX_REPORTED | **Architekt niezależnie potwierdza defekt produktu `SHIFT-24-PAIR-01`; Symulator B i generator pozostają bez zmian.** Solver już wymusza tę samą osobę/zestaw na obu połowach H24. False-positive powstaje w `_check_24h_same_person()`, bo surowy overlap czasowy dolicza PRIMARY z innego legalnie konkurującego demandu. Naprawa nie może jednak po prostu ufać `covers_demand_id`, bo otworzyłaby T022-F2. Zalecenie: wydzielić/zreużyć jedno źródło prawdy z obecnej semantyki atrybucji `COVERAGE-01` (T041: tag rozróżnia tylko realnie konkurujący podprzedział; spanning/manual real coverage nadal liczy się geometrycznie) i z tej samej atrybucji budować employee sets H24. Mały corrective Task produktu, `WHERE_MAP: REQUIRED`; bez zmiany solvera, chyba że osobny repro ją wykaże. Seed 0 zachować jako integracyjny reproduktor. Ujawnianie odrzuconego kandydata przy `TECHNICAL_ERROR` pozostaje osobnym tematem/ew. decyzją OWNERA i **nie blokuje** naprawy validatora. Dokument architekta: `arch/ARCHITECT_RESPONSE_VARIANT_B_SHIFT24_PAIR_2026-08-31.md` @ `a8b735e`; Codex: `arch/CODEX_RESPONSE_VARIANT_B_SHIFT24_PAIR_2026-08-31.md` @ `f48a840`. |
