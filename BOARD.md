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
| ROTA-T065-BRIEF | Codex | CC | `task/ROTA-T065` | brief `1145c9a`; audyt `37bc7f7` | CODEX_REPORTED | **PASS PREIMPLEMENTATION — można implementować dokładny brief.** Nie znaleziono drugiego solvera, generatora, membershipu, SiteRule ról, retry per rola, external rescue ani kopii prawa/manual correction/deviation/audytu. `allowed_roles` (kwalifikacja osoby) i `required_role` (wymaganie demandu) są różnymi stronami jednego istniejącego przepływu, nie dwiema kopiami logiki; niezależny validator pozostaje wymaganym anti-drift mirror. Granica reżimów sprawdzona: T023b 24h-rest floor i WEEKLY-REST-01 pozostają wyłącznie OCHRONA; nowe ORDINARY nie może dostać NIGHT-STREAK/DAY_ONLY-N/D-N SiteRule/external restriction ani rytmu D/N/W/W przez klasyfikację godzin. `THIRD-CONSECUTIVE-SHIFT-01` pozostaje aktywne także dla ORDINARY, ponieważ T058/OWNER_FINAL zamroził je globalnie jako „wszystkie 3 zmiany pod rząd” — to nie przeciek Ochrony i T065 nie może tej reguły zmieniać. Wspólne istniejące enabled/availability/REST/LOAD/SiteRule są reużywane tylko według własnych kontraktów. Po implementacji audyt wymaga jawnej macierzy obu reżimów, nie jednego happy path. Raport: `tasks/ROTA-T065/round_01/tests/tests_r1.txt`. |
