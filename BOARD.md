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
| BOARD-03 | CC | Codex + Architekt | docs/variant-b-joint-evaluation-batch2 | b445ee4 | READY_FOR_CODEX | **OWNER: zamiast budować formalny evaluator teraz, robimy jedną wspólną ręczną rundę oceny na Wariancie B po T045** ("zasady pracy zostawiam wam do ustalenia" -- architekt nie ma lokalnego wykonania kodu, więc CC generuje dane, wszyscy troje oceniają). 90 świeżych obiektów (seedy 30-119, generator niezmieniony, `main@4a0ea20` czyli po naprawie T045), surowe JSON-y: `tasks/ROTA-T044/round_01/tests/reports/batch2/`. Wszystkie 90: `final_result.status=FEASIBLE`, zero HARNESS_EXCEPTION. **Podział**: CC seed30-59, Codex seed60-89, architekt seed90-119 (czyta JSON-y z tego brancha, nie uruchamia niczego). Dyscyplina jak przy Wariancie A: `BRAK_UWAG`/`DO_SPRAWDZENIA`/`BRAK_DOWODU`, zero przeliczania faktów `validate()`/`rota/balance.py`, zero nowych progów, zero automatycznego Tasku z samego znaleziska. **CC swoją część skończył**: `arch/CC_JOINT_EVAL_SEEDS_30-59_2026-08-31.md`. Zero crashy; rozwiązane wcześniejsze pytanie o "brak kandydatów mimo FEASIBLE" z batcha 1 -- to było sprawdzanie `plan_result` (przed EXTERNAL) zamiast `final_result`, nie bug. Jedno realne `DO_SPRAWDZENIA`: **19/30 (63%) obiektów** ma pracownika z pełnym, nieskorygowanym `effective_target_hours` i mimo braku absencji `month_balance <= -20h` w finalnym grafiku (przykład: seed 47, -60h na 3 z 5 osób). Hipoteza: kalkulator obsady nie sprawdza rozkładu zapotrzebowania po dniach tygodnia. Silny kontrargument w samym produkcie: `final_result.warnings` na każdym z tych obiektów mówi `"quarter carry-in reset to 0"` -- Wariant B buduje izolowane pojedyncze miesiące bez kontekstu kwartału, więc mechanizm wyrównania `month_balance` przez `quarter_balance` nigdy nie ma szans zadziałać w tych danych; może to czysty artefakt testu, nie realny defekt. Nie rozstrzygam który. Czekam na Codex (seed60-89) i architekta (seed90-119). |
