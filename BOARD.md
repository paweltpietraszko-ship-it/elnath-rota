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
| ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT | Codex | OWNER | — (pre-brief finding) | main@`48c19bf` | OWNER_DECISION_NEEDED | **Problem potwierdzony, ale zapis „data Assignmentu/demandu” nie jest jedną testowalną regułą.** Ten sam `correctionEffectiveFrom=todayIso()` obsługuje przypisanie innej osobie, D6+/N6+, freeze, NN i usunięcie S1; kliknięcie wpisu nie resetuje daty. Pytanie do OWNERA: czy przy każdym otwarciu korekty istniejącego wpisu „Obowiązuje od” ma domyślnie przyjmować kalendarzową datę początku wybranego Assignmentu dla wszystkich operacji panelu, pozostając ręcznie edytowalne? Jeśli tylko D6+/N6+ albo data demandu, trzeba wskazać to wprost. Pełny audyt: `arch/PREBRIEF_AUDIT_2026-09-05_T056_FOLLOWUPS.md`. |
| ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS | Codex | OWNER | — (pre-brief finding, zależny od czytelnych deviations) | main@`48c19bf` | OWNER_DECISION_NEEDED | **Problem i konieczność backendowej blokady potwierdzone; brakuje semantyki potwierdzenia LAW bez finalizacji.** Checkboxy są dziś tylko lokalne, a `Deviation.acknowledged` zapisuje dopiero `Finalizuj`, które wymaga potwierdzenia wszystkich kategorii. Gdy LAW współistnieje z HOURS, użycie finalizacji pośrednio zablokuje eksport także przez HOURS, wbrew rulingowi „tylko LAW”. Pytanie do OWNERA: czy potwierdzenie LAW przy eksporcie jest jednorazową zgodą na ten wydruk, czy ma trwale ustawić acknowledged wraz z kto/kiedy bez finalizowania reszty? Brief musi też egzekwować blokadę na POST export i unieważniać stary lokalny PDF/Pobierz po zmianie wersji lub blokujących LAW. Pełny audyt: `arch/PREBRIEF_AUDIT_2026-09-05_T056_FOLLOWUPS.md`. |
| ROTA-DEVIATION-RAW-ASSIGNMENT-ID | Codex | OWNER | — (pre-brief finding, zależność PRINT-BLOCK) | main@`48c19bf` | OWNER_DECISION_NEEDED | **Problem potwierdzony dla całego trwałego kanału Deviation.** Mapper dopuszcza 13 built-in source classes plus dynamiczne SiteRule; `ViolationDetail.message` z osobą/skalą/oknem jest odrzucany, a API/UI pokazuje ogólną etykietę i surowy target. Sam frontend nie odtworzy prawdziwie LOAD/REST z current-month danych, bo validator widzi też boundary/other-site. Pytanie do OWNERA: czy „każdy typ ostrzeżenia w UI” oznacza wyłącznie trwałe pozycje panelu „Odchylenia”, czy także osobny banner SOFT, DECISION_REQUIRED i błędy innych ekranów? Pierwszy wariant jest zamkniętym taskiem; drugi wymaga osobnego inventory całej aplikacji. Brief dla Odchyleń musi objąć 13 sources + SiteRule, nie parsować message, nie nadpisywać targetu ani reason i wskazać jeden owner transportu faktów. Pełny audyt: `arch/PREBRIEF_AUDIT_2026-09-05_T056_FOLLOWUPS.md`. |
