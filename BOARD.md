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
| ROTA-EXCEL-VBA-ENGINE-ADAPTER | CC | Codex | `finding/excel-vba-engine-adapter` | `622bf69` (na `main@63f469f`) | READY_FOR_CODEX | **Nie Task, finding — decyzje właściciela z rozmowy eksploracyjnej, doprecyzowujące `proposals/ELNATH-ROTA-ENGINE-INTEGRATION-OPTIONS.md` (branch `proposal/engine-excel-integration-options`, Wariant D). Proszę Codexa o zweryfikowanie sekcji "Facts CC verified" w `arch/FINDING_2026-09-16_EXCEL_VBA_ENGINE_ADAPTER.md` względem realnego kodu (istniejąca autoryzacja `api/auth/context.py`, brak eksportu `.xlsx` w `schedule_export.py`) -- to są twierdzenia CC, nie zweryfikowany kontrakt. Po potwierdzeniu proszę przekazać architektowi do napisania właściwego briefu.** Decyzje właściciela w skrócie: VBA (nie Office Script) na klasycznym desktopowym Excelu, silnik w chmurze (Railway, sieć na miejscu potwierdzona), pełna funkcjonalność (odczyt + wywołanie PLAN/REPLAN), klucz dostępu zamiast interaktywnego logowania, jeden standardowy szablon `.xlsx` Roty oparty na własnym pliku właściciela z `Grafiki/` -- dopasowanie do cudzego istniejącego pliku klienta to osobna usługa programistyczna, poza rdzeniem SaaS. |
