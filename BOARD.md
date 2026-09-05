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
| ROTA-WORK-CODE-DURATIONS | CC | Architekt | — (brak brancha, brak brief.md) | `a42b493` (finding) | OWNER_DECISION_NEEDED | **Prośba o brief: definiowalne długości kodów zmian na wydruku (koniec kwartału).** Pełny opis: `arch/FINDING_2026-09-05_DEFINABLE_WORK_CODE_DURATIONS.md` (main@`a42b493`). **UWAGA dla Codexa/architekta: to NIE dotyka solvera ani katalogu zmian obiektu — tylko wydruku (`schedule_export.py`) i mapowania kodów (`site_repository.py`). Jeśli coś sugeruje zmianę w `rota/planning/solver.py`, to źle zrozumiane — pytać, nie zgadywać.** Skrót: przy zamykaniu kwartału koordynator ręcznie ustala pracownikowi dokładny `target_hours`; czasem trzeba jedną zmianę o niestandardowej długości (14h/17h/19h, inna za każdym razem, nie da się przewidzieć na sztywno), żeby dobić do celu. Dziś `FROZEN_WORK_CODE_HOURS` (`site_repository.py:51-54`) to zamrożona tabela dokładnie 10 wartości (D1-D5/N1-N5); `_map_work_code` (`schedule_export.py:306-320`) rzuca `WORK_CODE_MAPPING_REQUIRED` dla każdej innej długości — sprawdzone bezpośrednio, to realny blocker na wydruku, nie hipoteza. Ręczna korekta (`manual_edit.py::apply_manual_correction`) już dziś przyjmuje dowolną długość Assignmentu (zero odwołań do katalogu zmian, sprawdzone grepem) i WorkBalance/analityka liczy z realnego Assignmentu automatycznie (zero odwołań do wydruku) — czyli jedyna realna blokada jest w warstwie wydruku/mapowania kodów. Precedens już istnieje: `reserve_hours` dla U3-U5/C3-C5 (urlop/chorobowe) już dziś przyjmuje dowolną dodatnią wartość godzinową (`_validate_reserve_hours`), analogicznego mechanizmu brakuje po stronie realnych zmian roboczych D/N. Otwarte pytanie do architekta: czy taki definiowalny kod jest per-obiekt na stałe czy per-miesiąc (materiał referencyjny sugeruje per-miesiąc). CC nie projektuje rozwiązania — to pytanie kontraktowe. |
