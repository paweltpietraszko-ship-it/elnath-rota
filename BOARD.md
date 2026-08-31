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
| BOARD-01 | CC | Codex/architekt | task/ROTA-T044 | 8e76de2 | READY_FOR_CODEX | Naprawione oba znaleziska z `tests_r13.txt` (FAIL na `083d4c6`). R13-01: dodana `_readback()` wywołująca istniejące `get_analytics`/`get_month_view` (best-effort, błąd odczytu zapisywany jako dana, nie maskuje wyniku PLAN/REPLAN) -- każdy raport ma teraz `readback.analytics`/`readback.month_view` wypełnione. R13-02: `_write_completed_report()` już nie łyka wyjątku z samego zapisu (`except Exception: pass` usunięte) -- błąd zapisu propaguje się i przykład staje się czerwony, zamiast zostać cicho zielony bez raportu; `teardown()` opakowany w try/finally, żeby połączenie SQLite i tak się zamykało. Przy okazji zainicjalizowany `self.site_id = None` w `__init__` (wcześniej ustawiany tylko wewnątrz try w setup, mogło dać AttributeError z nowego `_readback()`). Dodane testy regresyjne dla obu. Zweryfikowane: ruff czyste, 61/61 testów niestanowych, maszyna stanów PASS (~161s), realne raporty z przebiegu mają wypełniony readback. Proszę o kolejny niezależny audyt/ocenę architekta. |
