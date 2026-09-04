# BOARD.md — kolejka przekazań CC ↔ Codex

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
| ROTA-T052 | CC | Architect | `task/ROTA-T052-s1-periodic-training-contract` | (implementacja w toku) | OWNER_DECISION_NEEDED | OWNER_CORRECTED 2026-09-04 (Paweł, po zamrożeniu brief.md round_03 PASS): S1 nadal NIE HARD-blokuje REST-01/WEEKLY-REST-01 (nie zmienia się nic z T52-05..T52-08), ale realne naruszenie 11h/35h wokół S1 nie może być milczące -- "nie możemy świadomie pisać programu łamiącego prawo". Zaimplementowane w `validator.py` (`_check_rest`/`_check_weekly_rest` teraz przyjmują `warnings`, dopisują `REST-01 SOFT`/`WEEKLY-REST-01 SOFT` zamiast cichego `continue`) -- ręcznie zweryfikowane trzema scenariuszami (za krótki odpoczynek po S1 -> SOFT nie HARD; realny overlap S1 -> nadal HARD jak wcześniej; S1 psujące WEEKLY-REST-01 -> SOFT z realną liczbą wolnych godzin). Ma to zaskakującą konsekwencję: `report.warnings` z `validate()` jest DZIŚ martwym kodem -- ani `select_candidate`, ani `apply_manual_correction` go nigdzie nie przekazują (już istniejące SOFT ostrzeżenia typu `DAY_ONLY-N-FALLBACK-01 SOFT` mają ten sam los, to nie coś, co T052 zepsuło). Żeby koordynator faktycznie zobaczył ten SOFT warning, trzeba dodać pole do odpowiedzi w `api/routers/manual_edit.py` (i/lub trwałą widoczność przy odczycie w `rota/application/open_month.py`) -- żaden z tych plików nie jest w TASK_SCOPE. Proszę o decyzję: rozszerzyć zakres o któryś z nich, czy inaczej to zaadresować. Pozostałe dwa otwarte punkty bez zmian: (1) `rota/planning/constraints.py` nadal potrzebny dla realnej wykonalności PLAN/REPLAN wokół S1; (2) 3 testy ze sztywnym `LATEST_SCHEMA_VERSION == 10` nadal czekają na dopisanie do zakresu. |
| ROTA-T054 | Codex | Architect/CC | `task/ROTA-T054-persisted-plan-preview-contract` | `010d7d3ac25e97836e5d35c50fde14eabc02d222` | CODEX_REPORTED | PASS — READY_FOR_IMPLEMENTATION. Raport: `tasks/ROTA-T054/round_01/tests/tests_r1.txt`. Audyt potwierdził mały trwały rekord bez nowego ScheduleStatus i bez zmiany solvera; obejmuje także „Szukaj dalej” i ponowienia REPLAN. |
