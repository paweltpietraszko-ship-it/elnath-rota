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
| ROTA-T065 | Codex | Architekt | `main` (finding + zweryfikowany scope, brak briefu) | finding `3d9600f`; scope `66181cf`; re-check `c60f944` | CODEX_REPORTED | **ARCHITEKT — OWNER doprecyzował krytyczną zasadę: NIE tworzyć drugiej logiki, drugiego przebiegu ani drugiego solvera.** T065 NIE obejmuje `UCZEN` ani ekipy sprzątającej. Obejmuje tylko dwie rozłączne role: `KIEROWNIK` oraz `SPRZEDAWCA/ZALOGA`; zwykła obsada/rotacja odbywa się wyłącznie w tej samej roli. Jeżeli kierownik ma pracować jako sprzedawca, solver NIE podejmuje takiej decyzji i NIE wykonuje fallbacku. To jawna decyzja koordynatora: koordynator dopisuje tę osobę do załogi istniejącym mechanizmem, po czym kolejny zwykły PLAN/REPLAN działa na zaktualizowanej obsadzie. `EXTERNAL_SUPPORT` zachowuje dokładnie tę samą filozofię: niczego nie obserwujemy, nie szukamy automatycznie, nie uruchamiamy osobnego przebiegu ani osobnego mechanizmu doboru; program czeka na dopisanie kolejnej osoby do obsady przez koordynatora, a potem używa normalnego solvera. Jeśli Architekt nie zna istniejącego flow dopisywania osoby/obsady lub integracji z solverem, ma NAJPIERW przeczytać kod i użyć istniejącego mechanizmu, nie projektować nowego. Skład ról jest per obiekt: część sklepów ma tylko sprzedawców, inne wymagają kierownika + sprzedawcy; w sklepie referencyjnym jest 4 kierowników do wyboru. Solver ma układać obie pule na wspólny miesiąc według ogólnych reguł czasu pracy dla dorosłego handlu, nie profilu Ochrona. Grafiki historyczne są niemodyfikowalne — HARD. Wydruk pozostaje drugim zależnym Taskiem i łączy wszystkie role z historycznej wersji grafiku. `UCZEN` pozostaje osobnym przyszłym Taskiem z własnym reżimem prawa pracy. |