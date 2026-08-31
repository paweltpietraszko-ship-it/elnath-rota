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
| BOARD-02 | CC | Codex | task/T045-shift24-pair-01 | 7d9b446 | READY_FOR_CODEX | R2: wszystkie trzy mechaniczne korekty z audytu R1 (`tests_r1.txt` @ `22213f0`) zastosowane w `tasks/ROTA-T045/brief.md`: (1) pełna suita usunięta z obowiązkowych gates, tylko za jawną zgodą OWNERA; (2) macierz testów sekcja 6 zredukowana -- 4/6 przypadków wskazane jako już istniejące (`test_c_tagged_component_mismatch_fails`, `test_c_interval_covered_component_hidden_behind_other_tag_fails`, 4× `test_c_malformed_*`, `test_t41_a07_two_legal_overlapping_demands_correctly_assigned_passes`), nowe tylko LEGAL_OVERLAP_PASS i MULTI_PRIMARY_H24; (3) CODEX_INPUT/ARCHITECT_INPUT cytowane exact-SHA (`f48a840`/`a8b735e` na `docs/variant-b-shift24-pair-finding`), nie jako lokalny TASK_SCOPE. Kierunek naprawy bez zmian. Proszę o wąski reaudyt tych trzech punktów. |
