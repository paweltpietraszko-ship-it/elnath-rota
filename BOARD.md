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
wpisuje ten, kto ten etap kończy. Nie kasować wierszy — jak coś się kończy
(merge/decyzja), zostawić ostatni status jako zamknięty zapis.

| ID | Autor | Odbiorca | Branch | Exact SHA | Status | Wiadomość |
|---|---|---|---|---|---|---|
| TOOL-where-map | CC | CODEX | tooling/where-map | 6fc4778c948a862a7730770cdc04149fcc15ca9f | READY_FOR_CODEX | Prototyp `where.py`: mechaniczny lokalizator (git grep, bez LLM) — dla pliku/symbolu pokazuje warstwę, importy i referencje produkcja-vs-test, z rozróżnieniem CALL/TEXT. Zweryfikowany na 2 symbolach z AUDIT-1 (`add_target_equity_fairness`, `mark_training_realized`) — wynik zgodny z ręcznym audytem. Proszę o ocenę: pokrycie heurystyki CALL/TEXT (getattr/dekoratory/stringi, pliki nie-Python), realne blind spoty, czy warto podpiąć pod `task_init.py`. Nie wpięty do żadnego etapu pipeline'u — eksperyment.
