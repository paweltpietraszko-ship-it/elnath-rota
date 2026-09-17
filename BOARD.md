# BOARD.md — kolejka przekazań Architekt ↔ Codex ↔ CC

Każda nowa instancja Architekta przed podjęciem Tasku musi przeczytać w całości
`ARCHITECT_START_HERE.md`. Każda nowa instancja Codexa postępuje zgodnie z
`AGENTS.md` i `CODEX_START_HERE.md`.

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
| ROTA-ABSENCE-RANGE-REQUIRE-SECOND-CLICK | CC | Codex | task/ROTA-ABSENCE-RANGE-REQUIRE-SECOND-CLICK | 2c5f92f | READY_FOR_CODEX | Live UX fix (2026-09-17, owner click-through): absence date-range picker w `EmployeeAvailability.tsx` domykał zakres 1-dniowy już po pierwszym kliknięciu (react-day-picker `addToRange` bez `min`), włączając "Zgłoś" zanim koordynator zdążył wybrać drugi dzień. Owner wybrał opcję: zawsze wymagać jawnego drugiego kliknięcia, nawet dla 1 dnia. Zweryfikowane ręcznie na żywym dev-serwerze (realne obiekty/pracownicy); e2e regressiony w t062/t063/t064 sprawdzone przez `git stash` na czystej bazie — identyczne faile, niezwiązane z tą zmianą (pre-existing/środowiskowe). |
