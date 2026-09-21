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
| ROTA-RARE-WEEKLY-SLOT-PINNED | Architekt | CC | — (dalsza diagnostyka, bez implementacji) | `arch/FINDING_2026-09-21b_SATURDAY_CONCENTRATION_CONFIRMED_ON_REAL_BOLF.md` | READY_FOR_CODEX | **PRECHECK ARCHITEKTA: rzeczywisty objaw Bolf potwierdzony; mechanizm 'za słaba waga weekendu' i wykonalność równiejszego wariantu jeszcze NIEUDOWODNIONE.** Korekta poprzedniego findingu przyjęta: Bolf jest OCHRONA, 4/5 sobót w miesiącu, nie ORDINARY z jedną sobotą miesięcznie; styczniowe realne PLAN grupują 5/5 sobót u jednej osoby. ALE syntetyczny styczeń daje 2/3 sobót — to właśnie możliwie równy PODZIAŁ pięciu niepodzielnych zmian, a nie odtworzenie objawu 5/0. Przy 5 sobotach po 9h weekendowy spread 5/0 = 45h, 3/2 = 9h: `add_weekend_fairness` odróżnia te warianty przy pozostałych składnikach równych. Przed zmianą wagi, dodaniem SOFT 'nie kolejna sobota' lub pamięci między miesiącami CC ma wykonać JEDEN wąski eksperyment na identycznym realnym snapshotcie wejść Bolf (bez zapisu do DB/PII): wymusić wyłącznie w KOPII testowej podział sobót co najwyżej 3/2 i sprawdzić (a) czy istnieje HARD-feasible rozwiązanie przy niezmienionej reszcie demandów i fixed assignments, (b) jego łączny rozstrzał committed-hours, weekend spread, pozostałe SOFT, status OPTIMAL/FEASIBLE, objective/best bound/gap i czas vs wynik bez wymuszenia, (c) czy wymuszenie pozostawia taki sam minimalny rozstrzał godzin i czy 1% relative gap może maskować subtelny tie-break weekendu; dla porównania uruchomić w izolacji kontrolę z dokładniejszym gap/ewentualnie dłuższym czasem, NIE zmieniając parametrów produkcyjnych. Jeśli realnego snapshota nie da się bezpiecznie odtworzyć, napisz wprost, które dane są brakujące — nie zastępuj go syntetycznym 2/3 ani nie deklaruj root cause. Dopiero dowód powie czy weekend SOFT przegrywa z ważniejszym wyrównaniem całych godzin/HARD, czy jest remisem niewyróżnionym przez solver/gap, i czy poprawka w ogóle jest potrzebna w objective. Propozycja OWNERA 'nie ta sama osoba co poprzednia sobota' pozostaje kandydatem SOFT, NIE zatwierdzonym globalnym HARD ani automatyczną regułą przekraczającą miesiące. Raport + minimalna rekomendacja na branchu/arch finding, przekazanie przez BOARD do Architekta; brak implementacji produkcyjnej i merge, niezależny audyt kiedy dostępny. |
