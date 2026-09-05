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
| ROTA-SOLVER-RHYTHM-VS-TARGET | CC | Architekt | — (brak brancha, brak brief.md) | `17c2657` (finding) | OWNER_DECISION_NEEDED | **Prośba o brief: solver poświęca rytm D/N/W/W i unikanie 3 zmian pod rząd dla precyzji equity w target_hours, nawet gdy target strukturalnie nieosiągalny.** Pełny opis: `arch/FINDING_2026-09-05_SOLVER_RHYTHM_VS_TARGET_PRECISION.md` (main@`17c2657`). Skrót: obiekty mają zwykle nadwyżkę zatrudnienia (bufor na urlopy/L4), więc suma `target_hours` przewyższa realne zapotrzebowanie — część niedoboru jest z góry nieunikniona. Mimo to `add_target_equity_fairness` (`fairness.py:139-168`) dalej wyrównuje procent realizacji między pracownikami z dokładnością co do godziny, kosztem rytmu D/N/W/W i unikania 3 zmian pod rząd (`DN_RHYTHM_REWARD_WEIGHT`/`THIRD_CONSECUTIVE_SHIFT_PENALTY_WEIGHT` = 1, matematycznie zdominowane przez `TARGET_DEVIATION_WEIGHT`+equity, `solver.py:493-514/549-554`, OWNER_CORRECTED 2026-08-25). OWNER: koordynator w realnej pracy **nigdy** nie robi 3 zmian pod rząd — to bliżej HARD niż SOFT. Program już ma na to gotowy mechanizm: `DECISION_REQUIRED` (`engine.py`, dziś używany dla REST-01/LOAD-01/MEMBERSHIP-01), ale "3 zmiany pod rząd" nie jest do niego podłączone. 3 otwarte pytania projektowe w dokumencie (poziom priorytetu dla 3-zmian-pod-rząd vs ogólnego rytmu, czy equity potrzebuje pasma tolerancji, czy to jeden mechanizm czy dwa). CC nie projektuje rozwiązania — dotyka solvera, wymaga architekta. |
| ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT | Codex | Architekt | — (pre-brief finding) | main@`48c19bf` | CODEX_REPORTED | **OWNER_ACCEPTED 2026-09-05: historyczna służba jest faktem rozliczeniowym.** Przed rozpoczęciem pozostają zwykłe korekty planu; system sam bierze datę początku Assignmentu, bez ręcznego `effective_from`. Po rozpoczęciu kod/godziny/demand/stan/freeze są niezmienne; dopuszczalne jest tylko zapisanie, z obowiązkową przyczyną i historią, innego pracownika, który faktycznie wykonał całą służbę. Backend ma być ownerem blokady. To osobny brief ochrony historycznej służby, nie zmiana T056. Pełny kontrakt zachowania: `arch/PREBRIEF_AUDIT_2026-09-05_T056_FOLLOWUPS.md`. |
| ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS | Codex | OWNER / Architekt | — (pre-brief reaudyt, zależny od czytelnych deviations) | main@`e4d1504` | OWNER_DECISION_NEEDED | **CC znalazł główny mechanizm, ale nie wszystkie luki.** Poza wszystkimi korektami current zmieniają także `REPLAN` i `restore`; stary Blob PDF przeżywa korektę/REPLAN/restore oraz zmianę miesiąca; zapisane deviations mogą być nieświeże wobec boundary/other-site; a obecne `deviation_id=DEV-{index}-{rule}` koliduje między różnymi problemami — reproduktor: dwa różne REST-01 dla EMP-A/EMP-B dostały to samo `DEV-0-REST-01`. Nie wolno naprawić przez „druk tylko FINAL”, bo zamrożone T020/T047 eksportują legalny WORKING przed finalizacją. Jedna lista Odchyleń może obsłużyć zarówno Finalizuj, jak i jednorazowe potwierdzenie LAW dla PDF, ale backend musi świeżo walidować fingerprint+revision, a nie ufać ID/boolean. Jedyna decyzja OWNERA: po korekcie FINAL rekomendowane jest automatyczne przejście/fokus do tej samej listy z komunikatem „Grafik zmieniono — sprawdź ponownie odchylenia”, zamiast automatycznego otwierania finalizacji. Pełny reaudyt: `arch/PREBRIEF_REAUDIT_2026-09-05_PRINT_LIFECYCLE_UI_IDENTIFIERS.md`. |
| ROTA-DEVIATION-RAW-ASSIGNMENT-ID | Codex | Architekt / CC | — (pre-brief finding, zależność PRINT-BLOCK) | main@`e4d1504` | CODEX_REPORTED | **OWNER_ACCEPTED 2026-09-05: wszystkie techniczne identyfikatory mają zniknąć z całego UI koordynatora.** CC nie wykonał jeszcze pełnego inventory. Reaudyt potwierdził dalsze powierzchnie: Overview drukuje employee_id; Decisions ma fallback ID/requested_by/linked action IDs/raw condition; History pokazuje coordinator/source/decision/action/rule IDs i ID w before/after; Export pokazuje revision hash, siteId w nazwie pliku i dwa kody hash na PDF; Analytics pokazuje siteId; wspólny klient renderuje surowe `body.detail`, a backend detail często zawiera wewnętrzne ID. To minimalne source inventory, nie zamknięcie runtime — CC/architekt ma dokończyć realne ścieżki wszystkich ekranów i jawnie podzielić Taski. „LAW Godziny” nadal nie wystarcza. Audyty: `arch/PREBRIEF_AUDIT_2026-09-05_T056_FOLLOWUPS.md` oraz `arch/PREBRIEF_REAUDIT_2026-09-05_PRINT_LIFECYCLE_UI_IDENTIFIERS.md`. |
