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
| ROTA-T056 | Codex | Architect | `main` (brief only; implementation HOLD) | audited brief `e4260555645c5c00a3829bacf28bcc1233422f47` | CODEX_REPORTED | **PREIMPLEMENTATION AUDIT R2 — korekta fałszywego pozytywu.** Raport: `tasks/ROTA-T056/round_01/tests/tests_r2.txt`. R1 błędnie założył możliwość późniejszej zmiany standardowego D1–D5/N1–N5; PRODUCT_TRUTH je zamraża. Punkt kolizji przez „drugi zapis”, związane żądanie dwóch write boundaries i duplicate validation w read/export są wycofane; nie ma tu decyzji OWNERA. T56-03 wystarcza: owning boundary zapisu D6+/N6+ odrzuca kolizję z zamrożonym kodem standardowym lub innym dodatkowym kodem. **OWNER_CORRECTED PDF:** legenda zawiera tylko kody faktycznie użyte; gdy nie mieszczą się czytelnie na stronie grafiku, drukować drugą stronę ze wszystkimi użytymi oznaczeniami; bez obcięcia/ukrycia/nieczytelnego zmniejszania. Architekt ma w jednej rundzie przenieść ruling do briefu i poprawić pozostałe mechaniczne F1/F2/F3/F5/F6 z R2. Następnie wąski re-audyt exact SHA; kod produktu nadal wstrzymany. |
