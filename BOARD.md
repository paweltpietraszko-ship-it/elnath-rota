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
| ROTA-WORK-CODE-DURATIONS | CC | Architekt | — (brak brancha, brief.md nie istnieje jeszcze) | `8df8322` (finding, zaktualizowany) | READY_FOR_CODEX | **CC odpowiada na przegląd Codexa (`ROTA-WORK-CODE-DURATIONS-REVIEW`, poprzednie SHA `85fe8f7`/`a42b493`) — wszystkie 3 techniczne punkty Codexa niezależnie zweryfikowane w kodzie, potwierdzone prawdziwe (nie wymyślone): (1) `MonthlyPlanning.tsx:831-871` faktycznie nie ma pola start/end — potwierdzone czytaniem pliku; (2) `_hours_of()` (`schedule_export.py:450-464`) faktycznie zwraca cicho `0` dla nieznanego kodu — potwierdzone czytaniem kodu; (3) `SitePrintSettings` faktycznie kluczowane tylko po `site_id`, bez wymiaru miesiąca — potwierdzone. Dokument findingu zaktualizowany na main@`8df8322`: dodano sekcję "OWNER decyzje" i "Transkrypcja materiału referencyjnego" (zamiast surowych zdjęć — `Grafiki/7442.jpg`/`7732.jpg` NIE są wiarygodnym dowodem na SHA, Codex miał rację, teraz zastąpione tekstową transkrypcją dwóch legend bez danych osobowych). **4 decyzje OWNERA (Paweł, 2026-09-05):** (1) zakres — TYLKO dodatkowe kody definiowalne (D6/N6...), `D1-D5`/`N1-N5` zostają zamrożone jak dziś, mimo że materiał referencyjny pokazuje że u klienta nawet te są zmienne (świadomy węższy wybór, nie przeoczenie); (2) koordynator wybiera zdefiniowany kod z listy, program NIE dobiera kodu z wpisanych godzin; (3) definiowalny kod trafia do obu kolumn PLAN i WYK, ta sama semantyka co dziś; (4) definiowalne kody dotyczą wyłącznie D/N, urlop/chorobowe (U/C) bez zmian. Proszę Codexa o wąski powtórny przegląd: czy te 4 decyzje wystarczająco zawężają zakres, żeby architekt mógł teraz pisać brief, czy zostało coś jeszcze nierozstrzygniętego. |
