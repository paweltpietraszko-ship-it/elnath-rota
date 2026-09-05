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
| ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT | Architekt | Codex | — (brak brancha, bug znaleziony w istniejącym kodzie) | task/ROTA-T056@`6b66ac5` w chwili testu | READY_FOR_CODEX | **ARCHITECT: realny bug UX/semantyki, wysoki priorytet; niezależny od T056.** `correctionEffectiveFrom=todayIso()` jest bezpiecznie wyglądającym, ale błędnym defaultem dla korekty wcześniejszego Assignmentu: zapis jest technicznie poprawny, lecz dzień przed `effective_from` pozostaje na parent version i PDF pokazuje starą wartość. Rekomendowany minimalny kierunek do audytu: przy otwarciu korekty defaultować `effective_from` do daty korygowanego Assignmentu/demandu. Bez nowych warning subsystemów ani zmian wersjonowania; obecna możliwość ręcznej zmiany daty zostaje. |
| ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS | OWNER | Codex | — (brak brancha, finding produktowy) | task/ROTA-T056@`6b66ac5` w chwili testu | READY_FOR_CODEX | **OWNER RULING (2026-09-05): wariant 1 — blokada.** Eksport/druk (`POST .../schedule/{month}/export`, przyciski "Wygeneruj podgląd PDF"/"Pobierz") ma być zablokowany, dopóki wszystkie nieodhaczone deviations kategorii `LAW` (dziś: REST-01/WEEKLY-REST-01) nie zostaną acknowledged — ta sama reguła co dziś gate'uje `Finalizuj`, rozszerzona na eksport. Inne kategorie (COVERAGE/HOURS/PREFERENCE/...) NIE blokują — tylko LAW. OWNER: blokada bez czytelnego komunikatu jest bezwartościowa — patrz `ROTA-DEVIATION-RAW-ASSIGNMENT-ID` niżej, ta sama sesja OWNERA. Nie implementować blokady w oderwaniu od czytelności komunikatu, który koordynator zobaczy w momencie zablokowania. |
| ROTA-DEVIATION-RAW-ASSIGNMENT-ID | OWNER | Codex | — (brak brancha, bug znaleziony w istniejącym kodzie) | task/ROTA-T056@`6b66ac5` w chwili testu | READY_FOR_CODEX | **ARCHITECT: realny bug prezentacji; niezależny od T056.** Dla LOAD-01 `deviation_mapping._affected_target()` spada do surowego `assignment_id`, a UI wyświetla `affected_assignment_or_employee` bez tłumaczenia. Koordynator dostaje techniczny identyfikator zamiast informacji operacyjnej, mimo że validator już posiada employee_id, liczbę godzin i rolling-7d window w `ViolationDetail.message`. Wąski audyt ma znaleźć najmniejszą poprawkę prezentacji/targetowania bez tworzenia nowego Deviation DTO/subsystemu; zachować regułę, że koordynator nie widzi nic niemówiących symboli systemowych. **OWNER RULING (2026-09-05), rozszerzenie zakresu: dotyczy wszystkich kategorii deviations, nie tylko LOAD-01/HOURS** — koordynator ma dostawać zrozumiały komunikat (kogo dotyczy, czego dotyczy, jaka skala/kierunek naruszenia) dla KAŻDEGO typu ostrzeżenia pokazywanego mu w UI, nie tylko dla REST-01/WEEKLY-REST-01 objętych dzisiejszym `_EMPLOYEE_TARGETED_SOURCES`. System dziś zakłada, że koordynator zna znaczenie każdego kodu/kategorii/sygnatury na pamięć — to fałszywe założenie, ma zniknąć wszędzie, nie punktowo. Priorytet podniesiony: `ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS` (blokada eksportu na LAW) zakłada, że koordynator rozumie komunikat, który go blokuje — te dwa findingi są od teraz zależne, audytować razem lub w kolejności RAW-ASSIGNMENT-ID → PRINT-BLOCK. |
