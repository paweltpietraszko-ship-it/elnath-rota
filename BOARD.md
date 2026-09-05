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
| ROTA-T056 | CC | Architekt | `task/ROTA-T056` | `09995f6` (persistence/API layer only, zatrzymane przed §8/9) | OWNER_DECISION_NEEDED | **CC — blocker znaleziony podczas implementacji, nie złapany w 5 rundach preimplementation audytu.** Zaimplementowane i zweryfikowane bezpośrednio (nie tylko skompilowane): §4-7 brief e5dc5e1 — migracja 13, `site_repository.py` (`MonthlyExtraWorkCodes`, walidacja rodzina/suffix/duration-całkowite-godziny, wspólny invariant kolizji na obu write boundaries, zweryfikowany żywym reproduktorem w obie strony), `durable_inputs.save_monthly_extra_work_codes` (unified action history), `api/routers/export.py` (GET/PUT subresource). **Zatrzymane przed §8 (ręczna korekta) i §9 (mapowanie eksportu):** `schedule_export.py::_validate_item` (linia 158-164) wymaga, żeby `Assignment.start_datetime/end_datetime` DOKŁADNIE zgadzały się z `ShiftDemand` wskazywanym przez `covers_demand_id` — inaczej rzuca `WORK_PROVENANCE_INCOMPLETE`. Brief §8 każe zbudować korektę, która zachowuje ten sam `covers_demand_id` przy zmienionym (niestandardowym) czasie trwania — to jest dokładnie scenariusz, który ten check odrzuca. Zreprodukowane empirycznie: 12h zmiana D (06:00-18:00) z demandem, `end_datetime` ręcznie wydłużone do 23:00 (17h), ten sam `covers_demand_id` → `generate_schedule_pdf` zwraca `WORK_PROVENANCE_INCOMPLETE: actual interval contradicts its covered demand`. Reproduktor: `tasks/ROTA-T056/round_01/tests/cc_blocker_r6_work_provenance.py` (main@`09995f6` na branchu tasku), wyjście w `..._output.txt`. CC nie zgaduje naprawy (rozluźnienie `_validate_item` albo nowy sposób tworzenia demandu to realne decyzje projektowe spoza TASK_SCOPE) — potrzebna decyzja architekta/OWNERA, jak §8/9 mają współistnieć z tym istniejącym inwariantem. **OWNER (Paweł, 2026-09-05) potwierdził po wyjaśnieniu nieporozumienia: solver ma zostać całkowicie nietknięty (to nigdy nie było kwestionowane — `_validate_item` żyje w `schedule_export.py`/ręcznej korekcie, nie w solverze), i zgadza się, że tę konkretną kontrolę trzeba poluzować dla przypadku miesięcznych dodatkowych kodów D6+/N6+. Prośba do architekta: zaprojektować dokładny, wąski kształt tego poluzowania** — np. czy `_validate_item` ma akceptować rozbieżność `Assignment` vs `ShiftDemand` tylko wtedy, gdy różnica dokładnie odpowiada zapisanemu miesięcznemu extra code tej samej rodziny/dnia (nie każdą dowolną rozbieżność), czy potrzebny jest inny mechanizm — to jest decyzja projektowa dla wspólnego inwariantu używanego też przez inne taski, CC nie ustala tego sam. |
