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
| ROTA-EXCEL-VBA-ENGINE-ADAPTER | CC | Architekt | `finding/excel-vba-engine-adapter` | `dd64d4b` (Codex fact-check `d2a786a` na `622bf69`/`main@63f469f`) | CODEX_REPORTED | **OWNER RULING zapisany w findingu: standardowy artefakt zostaje czystym `.xlsx`; VBA (przycisk, konfiguracja klucza, wywołanie PLAN/REPLAN) dostarczany osobno jako jednorazowo instalowany dodatek (`.xlam`) -- unika powtarzającego się ostrzeżenia Excela o makrach przy każdym otwarciu, co dla tego profilu użytkownika (emerytowani funkcjonariusze) uznano za istotne tarcie. Blocker z audytu Codexa zamknięty. Reszta findingu (VBA/desktop Excel, silnik Railway, klucz dostępu, jeden szablon oparty na `Grafiki/`) bez zmian i gotowa do briefu.** Drobne korekty Codexa dla architekta: obecny auth to JWT w cookie (bez BearerTransport); logika projekcji grafiku w `schedule_export.py` istnieje, ale jest prywatna/PDF-owa, brief powinien wskazać minimalny wspólny szew zamiast zakładać gotowy helper. Pełny tekst: `arch/FINDING_2026-09-16_EXCEL_VBA_ENGINE_ADAPTER.md` na branchu `finding/excel-vba-engine-adapter`. |
