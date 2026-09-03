# BOARD.md — kolejka przekazań CC ↔ Codex

Nie czytane automatycznie jak AGENTS.md — trzeba wprost polecić "na początku
czytaj BOARD.md" (patrz AGENTS.md). To jest wyłącznie dziennik przekazania:
kto, co, na jakim SHA, gdzie leży raport. Żadnych ustaleń produktowych,
żadnych decyzji właściciela — te nadal trafiają do brief.md/kontraktu danego
Tasku. PR pozostaje realnym wyzwalaczem pracy; ten plik tylko rejestruje
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
| BOARD-06 | CC | Codex | task/ROTA-T047 | ffd0031 | READY_FOR_CODEX | Brief `ROTA-T047` gotowy do preimplementation audytu. Źródło: `manual_trials/Ochrona_2026-09/RAPORT.md` na `manual/ochrona-scenarios@53722e3` — realna próba czterech obiektów przez produkcyjne PLAN/select/eksport, bez ręcznych demandów/Assignmentów. Dwa potwierdzone problemy: (1) `_validate_item` (`rota/application/schedule_export.py`) odrzuca każdy demand z `catalog_kind == OTHER` jako `UNSUPPORTED_SHIFT_KIND`, mimo że `_map_work_code` już potrafi dokładnie dopasować istniejące zamrożone kody D2=4h/D4=2h/N2=16h po rodzinie/godzinach/interwale — próba straciła PDF dla Placu (N2) i Urzędu (D2); (2) `_check_fits`/`_render_pdf` zakładają jeden arkusz A3 i zwracają `ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT` dla Parku Logistycznego (17 LOCAL) mimo poprawnego, akceptowalnego grafiku. CC zweryfikował przed przekazaniem: `FROZEN_WORK_CODE_HOURS`, ownership czterech symboli (po jednym callerze każdy, WHERE_MAP potwierdzony na `BASE_MAIN_SHA`), oraz że `OTHER` w `shift_catalog.py` oznacza tylko "czas trwania inny niż 12/24h", nie "niebezpieczny rodzaj pracy" — usunięcie wczesnej blokady niczego nie omija, `_map_work_code` sam failuje closed (`WORK_CODE_MAPPING_REQUIRED`) bez dopasowania. Brief explicite wyklucza dodanie kodu 14h (real trial użył istniejącego N2=16h jako obejścia), zmiany solvera/API/frontendu i nowy podgląd. `TASK_SCOPE`: `rota/application/schedule_export.py`, `tests/test_t020.py`, opcjonalnie `tests/test_t047_print_export.py`. Ryzyko odnotowane OWNEROWI: plik jest już na 603/600 (zaakceptowana nadwyżka z T046), paginacja prawdopodobnie pogłębi `SIZE_FILE` `WYMAGA_DECYZJI` — kryterium akceptacji to czytelność, nie sama liczba, decyzja zapadnie po zobaczeniu faktycznej nadwyżki. Dokument: `tasks/ROTA-T047/brief.md`. |
