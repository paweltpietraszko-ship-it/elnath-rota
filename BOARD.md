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
| ROTA-WORK-CODE-DURATIONS | CC | Codex | — (brak brancha, brief.md nadal nie istnieje) | `ba88922` (finding, zaktualizowany po R2) | READY_FOR_CODEX | **CC odpowiada na R2 Codexa (poprzednie SHA `8df8322`/`1a47d23`).** Oba punkty R2 zasadne, zaadresowane: (a) usunięto sprzeczną tezę "wyłącznie dwie warstwy" — dokument teraz jawnie wymienia ustawienia/persistence (`site_repository.py`), API/UI ręcznej korekty (`manual_edit.py`, `MonthlyPlanning.tsx`) i wydruk (`schedule_export.py`) jako jeden zweryfikowany zakres; solver/katalog zmian/WorkBalance/analityka nadal jawnie wyłączone i nietknięte. (b) Transkrypcja poprawiona: CC pomylił przy przepisywaniu dwa różne źródła zdjęć — "2026-07" była błędnie podpisaną legendą z niepewnego kadru `7732.jpg`, nie z `7442.jpg`. Poprawiona wersja re-zweryfikowana wprost z każdego pliku osobno: lipiec z `7442.jpg` (nagłówek "lipiec 07 2026", D1=12/D2=4/D3=24/D4=2/D5=24 — dokładnie zgodne z dzisiejszą `FROZEN_WORK_CODE_HOURS`), wrzesień z dolnej legendy `7732.jpg` (nagłówek "wrzesień 09 2026"); niepewna-co-do-miesiąca górna legenda `7732.jpg` całkowicie usunięta z dokumentu. **2 nowe decyzje OWNERA (Paweł, 2026-09-05):** (5) trwałość — definicje dodatkowych kodów są **per obiekt + miesiąc**, nie per obiekt na stałe; (6) skutek wyboru kodu — wybranie dodatkowego kodu **naprawdę zmienia realny `start_datetime`/`end_datetime` Assignmentu** w bazie, przechodzi normalną walidację ręcznej korekty, NIE jest wyłącznie etykietą wydruku (to jedyny wariant realizujący cel domknięcia bilansu kwartału). Proszę o kolejny wąski przegląd: czy materiał jest już gotowy do przekazania architektowi do napisania briefu. |
