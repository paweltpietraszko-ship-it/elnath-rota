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
| BOARD-07 | Codex | CC | task/ROTA-T048 | ab59c6b | OWNER_DECISION_NEEDED | Preimplementation audit R1: **STATUS: OWNER_DECISION_NEEDED — bez werdyktu PASS/FAIL** (OWNER_EXPLANATION_GATE). OWNER_CONFIRMED: ownerzy kodu i granica bez solvera/API poprawne, `DAY_SHIFT_OFF-01`/"checkbox"/status/employee_id→display_name/coordinator_id-poza-zakresem — wszystko OK, architekt niepotrzebny. Dwie realne `OWNER_DECISION_NEEDED`: (1) usunięcie `version_id` z historii wersji bez zamiennika sprawia, że dwie wcześniejsze wersje o tym samym statusie stają się nierozróżnialne — potrzebna decyzja, czy dodać czytelną datę utworzenia/`effective_from` (dane już są w API, zero nowego odczytu); (2) usunięcie `demand_id` z listy blokujących zmian zakłada błędnie, że sam zakres dat jednoznacznie identyfikuje demand — nieprawda przy dozwolonym nakładaniu się niezależnych zapotrzebowań (`arch/spec.md:58,485`) — decyzja, czy akceptować identyczne, nieodróżnialne linie w tym małym Tasku, czy rozszerzać opis (to drugie osobno oceniane pod kątem architekta). Dodatkowo dwie techniczne korekty bez decyzji OWNERA: carry-in warning nadal zawiera angielskie `target_hours` i błędnie nazywa cały bilans (może być ujemny) "nadgodziny" — zamrożony kontrakt analityki (`arch/T019_coordinator_analytics_architect_brief.md:43-50,254`) tego zakazuje, potrzebne neutralne brzmienie (propozycja w raporcie); `stateValueLabel` w History.tsx tłumaczyłby KAŻDY string "ORDINARY" w widoku, w tym wolny tekst użytkownika (`description`/`source`/`reason`) — trzeba zawęzić do klucza `planning_regime`. Reaudyt ograniczony do tych czterech punktów po korekcie, bez testów. Raport: `tasks/ROTA-T048/round_01/tests/tests_r1.txt` na `task/ROTA-T048@aec6f7d` (Codex trafił na limit sesji przed własnym pushem — plik dopisany i wypchnięty przez CC z treścią przekazaną przez OWNERA, bez zmian). |
