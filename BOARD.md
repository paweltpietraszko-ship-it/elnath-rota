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
| ROTA-T065 | Codex | OWNER | `main` (finding + zweryfikowany scope, brak briefu) | finding `3d9600f`; scope `66181cf`; re-check `c60f944` | OWNER_DECISION_NEEDED | **ARCHITEKT — ustalenia OWNERA z 2026-09-13 zapisane; brief jeszcze HOLD na jednym pytaniu o uczniów.** Role są rozłączne: `KIEROWNIK`, `SPRZEDAWCA/ZALOGA`, `UCZEN`; rotacja/obsada wyłącznie w tej samej roli. Skład ról jest per obiekt: są sklepy tylko ze sprzedawcami, inne wymagają kierownika + sprzedawcy, a uczniowie występują tylko w niektóre dni. W sklepie referencyjnym kierownik jest zawsze dostępny (4 osoby do wyboru). Ekipa sprzątająca WYŁĄCZONA z zakresu. Solver ma układać trzy niezależne pule roli na wspólny miesiąc, stosując ogólne reguły czasu pracy dla handlu, nie profil Ochrona; końcowy wydruk jest jeden i zawiera wszystkie role razem. Grafiki historyczne są niemodyfikowalne — HARD; historyczny wydruk nie może zmieniać roli po późniejszej zmianie membership, więc wymaga historycznej migawki/źródła z wersji grafiku, nie bieżącego membership. Architekt sprawdził aktualne reguły dla dorosłych: bazowo 8h/dobę, przeciętnie 40h i 5 dni/tydzień, min. 11h odpoczynku dobowego i 35h tygodniowego, przeciętnie max 48h z nadgodzinami; to nie jest profil Ochrona. **JEDNO PYTANIE DO OWNERA:** czy `UCZEN` może mieć mniej niż 18 lat? Jeżeli tak, potrzebuje osobnego profilu prawnego (czas nauki wliczany do pracy, odrębne limity, zakaz nadgodzin/nocy itd.) i nie może dziedziczyć reguł dorosłej załogi. Po odpowiedzi Architekt przygotuje brief kategorii; wydruk jako drugi zależny Task. |
