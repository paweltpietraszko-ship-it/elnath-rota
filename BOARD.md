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
| BOARD-01 | CC | Codex | task/ROTA-T043 | e95b502 | READY_FOR_CODEX | Wszystkie 5 ustaleń z `tests_r6.txt` naprawione: test_t009_plan_select_replan.py cofnięty dokładnie do main@c25c73e (diff pusty, potwierdzone przez CC); LEAVE_GRANTED max 1 osoba/14 dni, SICK_LEAVE do 21 dni; portfel losuje miesiąc na obiekt (wszystkie 12 miesięcy 2026 w 20 seedach); failure JSON teraz też dla FAIRNESS_UNPROVEN, z realną wykonalną komendą reprodukcji (CC uruchomił jedną niezależnie); oracle kwartalny liczy actual PRIMARY hours z realnych Assignmentów (nie z analytics) i sprawdza unresolved_carryover==quarter_balance. Regenerowany portfel: 16 FEASIBLE/3 CRASH (ten sam realny błąd produktu: SICK_LEAVE na już zaplanowany dzień w REPLAN, zachowany jako failure JSON, nie naprawiany)/1 DECISION_REQUIRED, Q3 nadal QUARTER_OK/QUARTER_BALANCE_PASS. 23/23 testów celowanych zielone (potwierdzone przez CC niezależnie). Bez pełnej regresji. |
