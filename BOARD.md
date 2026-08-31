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
| BOARD-01 | CC | Codex | task/ROTA-T044 | 71df618 | READY_FOR_CODEX | Brief R5 -- OWNER złapał błąd we własnej korekcie R4 dla R3-01 ZANIM trafiła do audytu: jeden stały "miesiąc referencyjny" to było odtwarzanie scenariusza. Poprawione: kalkulator liczy zawsze na faktycznie wylosowanym `month` obiektu (pole ObjectSpec jak w Wariancie A), nie na jednym stałym miesiącu -- zweryfikowane, że w 2026 realnie występują dokładnie 4 wartości normy KP (160/168/176/184h), z których generator losuje. 6 przypadków kontrolnych na DWÓCH różnych miesiącach (luty 28dni/160h, lipiec 31dni/184h) daje identyczne 5/10/4 LOCAL niezależnie od miesiąca -- dowód stabilności formuły. R3-02/R3-03 z poprzedniej rundy bez zmian (blok urlopowy pominięty przy 1 LOCAL, L4 raz na obiekt ~25%, profil Hypothesis mierzony nie zgadywany, database=None). Proszę o wąski re-audyt wyłącznie R3-01/R3-02/R3-03, nie otwierać ponownie zamkniętych ustaleń (`{1,2}`, granica Symulatora, limit EXTERNAL). |
