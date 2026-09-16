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
| ROTA-EXCEL-VBA-ENGINE-ADAPTER | CC | Codex | `task/ROTA-EXCEL-VBA-ENGINE-ADAPTER` | fix `ab26045` (na FAIL R6 `ae8518a`; raport `2fc2abd`) | READY_FOR_CODEX | **Poprawki R6-01/R6-02, tym razem przez realne ponowne użycie istniejących ownerów, nie kolejny skrót.** R6-01: `build_ad_hoc_day_grid` teraz faktycznie odpytuje kanoniczne fakty nieobecności i używa dokładnie tego samego prostego słowa na dzień co renderer PDF ORDINARY (`_collect_ordinary_absence`/`_ordinary_absence_word`) -- nie nowej dekompozycji, nie zależnego od `SitePrintSettings` coin-change OCHRONA, który nie pasuje do tego prostszego kontraktu wartości dnia. `conn`/`site_id`/`local_ids` są opcjonalne, więc zamrożony `audit_r5_repro.py` (czyste obiekty, brak bazy) działa bez zmian; realny endpoint (`_candidates_out`) przekazuje je zawsze. R6-02: `_validate_payload_shape` woła teraz bezpośrednio prawdziwe reguły semantyczne write-ownera (`_validate_time_window`, `_validate_delegation_hours` z `availability_repository.py`) plus jawny check `end_date >= start_date`, wszystko przed jakimkolwiek zapisem -- żadnej drugiej, uboższej kopii reguł. Weryfikacja: oba zamrożone reproduktory (`audit_r5_repro.py`, `audit_r6_repro.py`) + bezpośrednio dotknięte testy: 12/12 PASS. Szerszy zestaw z poprzednich rund: 210/211 PASS (ten sam 1 pre-istniejący, niezwiązany fail). `ruff check` czyste. |
