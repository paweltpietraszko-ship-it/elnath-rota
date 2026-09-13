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
| ROTA-T065 | Codex | Architekt | `main` (finding + zweryfikowany scope, brak briefu) | finding `3d9600f`; scope `66181cf`; re-check `c60f944` | CODEX_REPORTED | **ARCHITEKT — OWNER doprecyzował krytyczną zasadę: NIE tworzyć drugiej logiki, drugiego przebiegu ani drugiego solvera.** T065 NIE obejmuje `UCZEN` ani ekipy sprzątającej. Obejmuje tylko dwie role: `KIEROWNIK` oraz `SPRZEDAWCA/ZALOGA`; zwykła obsada/rotacja odbywa się wyłącznie w jawnie dopuszczonej roli. Jeżeli kierownik ma pracować jako sprzedawca, solver NIE podejmuje takiej decyzji i NIE wykonuje fallbacku. To jawna decyzja koordynatora: koordynator dopisuje tę osobę do załogi istniejącym mechanizmem, po czym kolejny zwykły PLAN/REPLAN działa na zaktualizowanej obsadzie. `EXTERNAL_SUPPORT` zachowuje dokładnie tę samą filozofię: niczego nie obserwujemy, nie szukamy automatycznie, nie uruchamiamy osobnego przebiegu ani osobnego mechanizmu doboru; program czeka na dopisanie kolejnej osoby do obsady przez koordynatora, a potem używa normalnego solvera. Skład ról jest per obiekt. Backend katalogu zmian JUŻ obsługuje pełnogodzinne zmiany 7–9h jako `ShiftCatalogKind.OTHER/INNY`; nie tworzyć drugiego generatora ani osobnego modelu godzin. Sklepy mogą być całodobowe i mieć nietypowe/nakładające się zmiany. Konfiguracja referencyjna 05–12/12–19/05–14 jest tylko fixture realnego sklepu, nie kontraktem systemu. Dla użytkownika/solvera źródłem prawdy są konkretne czasy; ewentualne 1/2/3 to wyłącznie pomocnicza etykieta, nie źródło logiki. T065 nie projektuje PDF sklepu; to osobny Task. |
| ROTA-T065-BRIEF | Architekt | Codex | `task/ROTA-T065` | `1145c9aef3b7ff7219f6520184874463d869bf08` | READY_FOR_CODEX | **WĄSKI PREIMPLEMENTATION RE-CHECK PO FALSYFIKACJI WORKA.** Brief: `tasks/ROTA-T065/brief.md`. OWNER: produkt ma działać dla różnych sklepów; sklep referencyjny to wyłącznie fixture. Nie budować ponownie prawa pracy, validatora, manual correction, deviations ani audit trail — reużyć istniejące mechanizmy tak jak w Ochronie. Work potwierdził: `INNY`/7–9h/generator już istnieją; `allowed_roles` + `required_role` nie dublują obecnych ról; globalny wymóg `solve_calls==1` był błędny; trzeba zachować istniejące etapy engine i tylko zakazać nowych retry per rola; `required_role` musi przejść przez PlanPreview→selection→ScheduleVersion/reload; `MonthlyPlanning` musi pokazywać konkretne godziny zamiast `?`; legacy `shift_kind=None` nie może stać się nową semantyką ORDINARY; PDF pozostaje osobno. Sprawdź minimalność oraz brak drugiego systemu. Implementation HOLD do PASS dokładnego SHA. |