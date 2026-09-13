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
| ROTA-T065 | Codex | OWNER | `main` (finding + zweryfikowany scope, brak briefu) | finding `3d9600f`; scope `66181cf`; re-check `c60f944` | OWNER_DECISION_NEEDED | **ARCHITEKT — zakres uproszczony po decyzji OWNERA 2026-09-13.** T065 NIE obejmuje `UCZEN` ani ekipy sprzątającej. `UCZEN` jest młodocianym na praktykach i wymaga osobnego przyszłego Tasku z odrębnym profilem prawa pracy oraz dodatkowymi danymi wejściowymi; nie dokładamy tego do obecnego solvera jako zwykłej kategorii. T065 obejmuje tylko dwie rozłączne role: `KIEROWNIK` oraz `SPRZEDAWCA/ZALOGA`. Obsada/rotacja wyłącznie w tej samej roli. Skład ról jest per obiekt: część sklepów ma tylko sprzedawców, inne wymagają kierownika + sprzedawcy. W sklepie referencyjnym kierownik jest zawsze dostępny (4 osoby do wyboru). Solver ma układać niezależne pule obu ról na wspólny miesiąc, stosując ogólne reguły czasu pracy dla dorosłego handlu, nie profil Ochrona. Grafiki historyczne są niemodyfikowalne — HARD. Wydruk pozostaje drugim zależnym Taskiem i ma łączyć wszystkie role z historycznej wersji grafiku, nie z bieżącego membership. **JEDNO PYTANIE DO OWNERA przed briefem:** jeżeli uruchamiany jest `EXTERNAL_SUPPORT`, czy osoba zewnętrzna też musi mieć dokładnie tę samą rolę co brakująca obsada (`KIEROWNIK` zastępuje tylko kierownika, `SPRZEDAWCA/ZALOGA` tylko tę rolę)? To jest reguła operacyjna, nie chcę jej zgadywać. |