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
| ROTA-EXCEL-VBA-ENGINE-ADAPTER | Architekt | Codex | `task/ROTA-EXCEL-VBA-ENGINE-ADAPTER` | brief `8fe4c90` (base `89f5aaa`) | READY_FOR_CODEX | **BRIEF_ONLY_PRECHECK.** Zamrożono wariant desktop Excel + osobny dodatek VBA `.xlam` + czysty `.xlsx` + Railway. Dodatek uruchamia PLAN/REPLAN i używa jednego standardowego szablonu. Nowy, wąski API-key auth jest alternatywnym wejściem do istniejącego `AccountMapping`, bez zmiany browser cookie auth. Brief wymaga wspólnego modelu projekcji grafiku zamiast kopiowania prywatnej logiki PDF. OWNER doprecyzował UX blockerów: użytkownik ma dostać po polsku konkretny problem i konkretne następne działanie, np. „A jest niedostępne — zrób C i F”, bez technicznych statusów jako treści; przy blockerze/błędzie arkusz pozostaje niezmieniony. Proszę o redukcję zakresu i sprawdzenie, czy kontrakt jest implementowalny bez nowej decyzji produktowej. |
