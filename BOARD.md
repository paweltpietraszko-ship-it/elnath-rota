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
| BOARD-01 | CC | Codex | docs/symulator-variant-b-request | 2619e1e | READY_FOR_CODEX | Prośba OWNER (2026-08-30): niezależny brief dla Symulatora Wariant B (prawdziwy generator, różne obiekty przy każdym uruchomieniu, nie stały zestaw 20 seedów jak Wariant A z T043). CC celowo nie pisze tego briefu (ten sam konflikt interesu co przy prośbie o T043 -- CC autor Wariantu A). OWNER wskazał wprost, że to NIE jest nowa prośba: instrukcja "nie chcę odtwarzania scenariuszy" była dana już przy T038 i została zignorowana przy pisaniu T043 brief.md bez wyjaśnienia -- brief.md ma teraz zawierać jawną sekcję odpowiadającą dlaczego. Pełny kontekst i cytaty OWNERA: `arch/REQUEST_SYMULATOR_WARIANT_B_2026-08-30.md` na tym branchu. |
