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
| ROTA-T065 | Codex | CC | `task/ROTA-T065` | implementacja `04d05c5`; audit FAIL + repro `8dc9a80` | CODEX_REPORTED | **FAIL na dokładnym `04d05c5`; raport: `tasks/ROTA-T065/round_01/tests/tests_r2.txt`, 5/5 niezależnych reproduktorów czerwonych.** R2-01: finalny/ręczny PRIMARY bez `covers_demand_id` może realnie pokryć demand KIEROWNIK osobą mającą tylko SPRZEDAWCA_ZALOGA, a validator nie zgłasza ROLE-01 ani COVERAGE-01. R2-02: new ORDINARY nadal niesie techniczne D/N i dziedziczy DAY_ONLY-01 oraz NIGHT-STREAK-01; UI nadal wystawia „Rodzaj: Dniówka/Nocka”. Globalne THIRD-CONSECUTIVE-SHIFT-01 jest prawidłowe i nie jest findingiem. R2-03: API przyjmuje ORDINARY bez wymaganej roli (204) oraz zapisuje rolę sklepową dla OCHRONA (204 + round-trip), więc granica reżimów nie jest szczelna; kontrolki roli w UI także nie są bramkowane reżimem. Nie znaleziono drugiego solvera/pipeline ani zbędnej równoległej domeny — to trzy wąskie defekty istniejących ownerów. Testy Tasku + celowane regresje: 91 passed. Historyczny test T023 jest stale source-shape proof wobec jawnie autoryzowanych zmian T065, nie regresja i nie osobny bloker. Zamrożonych symulatorów/benchmarków ani pełnej regresji nie uruchamiano. Re-check po poprawce: tylko diff `04d05c5..NOWY_SHA`, zachowane repro R2, testy T065 i najbliższe celowane ścieżki. |
