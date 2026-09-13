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
| ROTA-T065 | Codex | OWNER | `main` (finding + zweryfikowany scope, brak briefu) | finding `3d9600f`; scope `66181cf`; re-check `c60f944` | OWNER_DECISION_NEEDED | **ARCHITEKT — ustalenia OWNERA z 2026-09-13 zapisane; brief nadal HOLD na jednym realnym rozróżnieniu prawnym uczniów.** Role są rozłączne: `KIEROWNIK`, `SPRZEDAWCA/ZALOGA`, `UCZEN`; rotacja/obsada wyłącznie w tej samej roli. Skład ról jest per obiekt: są sklepy tylko ze sprzedawcami, inne wymagają kierownika + sprzedawcy, a uczniowie występują tylko w niektóre dni. W sklepie referencyjnym kierownik jest zawsze dostępny (4 osoby do wyboru). Ekipa sprzątająca WYŁĄCZONA z zakresu. Solver ma układać niezależne pule roli na wspólny miesiąc, stosując ogólne reguły czasu pracy dla dorosłego handlu, nie profil Ochrona; końcowy wydruk jest jeden i zawiera wszystkie role razem. Grafiki historyczne są niemodyfikowalne — HARD; historyczny wydruk nie może zmieniać roli po późniejszej zmianie membership, więc wymaga historycznej migawki/źródła z wersji grafiku, nie bieżącego membership. OWNER potwierdził, że `UCZEN` ma 15–18 lat, więc to pracownik młodociany i MUSI mieć osobny profil prawny: do 16 lat max 6h/dobę, powyżej 16 lat max 8h/dobę; czas obowiązkowej nauki wlicza się do czasu pracy; brak nadgodzin i pracy nocnej; min. 14h nieprzerwanego odpoczynku obejmującego porę nocną oraz min. 48h nieprzerwanego odpoczynku tygodniowego obejmującego niedzielę; przy >4,5h pracy przerwa 30 min wliczana do czasu pracy. **JEDNO PYTANIE DO OWNERA:** w realnym sklepie uczniowie są zatrudnieni jako młodociani w celu przygotowania zawodowego, czy przy `pracach lekkich`? To zmienia solver: dla prac lekkich podczas zajęć szkolnych limit wynosi 12h/tydzień i max 2h w dniu szkolnym, natomiast przygotowanie zawodowe działa pod innym reżimem z czasem nauki wliczanym do pracy. Po tej odpowiedzi Architekt przygotuje brief kategorii; wydruk jako drugi zależny Task. |
