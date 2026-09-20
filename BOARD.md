# BOARD.md — kolejka przekazań Architekt ↔ Codex ↔ CC

Każda nowa instancja Architekta przed podjęciem Tasku musi przeczytać w całości
`ARCHITECT_START_HERE.md`. Każda nowa instancja Codexa postępuje zgodnie z
`AGENTS.md` i `CODEX_START_HERE.md`.

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
| ROTA-TARGET-HOURS-CEILING-NOT-BULLSEYE | Architekt | CC | `task/ROTA-TARGET-EQUITY-DIAGNOSIS` | eksperyment wag `438acae`; finding `arch/FINDING_2026-09-20_TARGET_HOURS_IS_A_CEILING_NOT_A_BULLSEYE.md` | READY_FOR_CODEX | **OWNER: target_hours jest sufitem, nie celem do dobijania; najpierw wąska weryfikacja mechanizmu, bez zmiany produkcyjnej.** Kontynuuj dotychczasową diagnostykę w izolowanym eksperymencie na tych samych danych Royal i obiektu ORDINARY: porównaj aktualne TARGET-01 (`pos+neg`) z wariantem karzącym TYLKO przekroczenie (`pos`), bez zmian innych wag, HARD, `_effective_targets` (odjęcie absencji i delegacji), limitów czasu/gap i ścieżki bilansu. Zapisz godziny wszystkich pracowników, rozstrzał, liczbę oraz jakość sekwencji D/N, walidację HARD, przekroczenia efektywnych limitów, status/gap i czasy (co najmniej 2 powtórzenia na obiekt). Sprawdź oddzielnie, czy bilans niedoboru nadal jest widoczny koordynatorowi. **Uwaga architekta:** wcześniejszy wynik wag 1/3/10/30 nie dowodzi, że samo `neg` powoduje nierówny podział: przy stałej obsadzie i braku przekroczeń suma `neg` jest stała dla każdego rozkładu; usunięcie jej może pozostawić ranking rozwiązań bez zmian. Jeśli wariant pos-only nie poprawi Royal, zbadaj na tym samym stanie realny wpływ innych SOFT (weekendy/święta/rytm) i 1% gap na wybór kandydata; nie ogłaszaj naprawy bez pomiaru. **Nie koduj ani nie merge'uj poprawki produkcyjnej, nie dodawaj HARD sufitu/nowych mechanizmów bez decyzji OWNERA.** Opisz wyniki i najmniejszy uzasadniony kierunek w raporcie na branchu zadania, bez danych osobowych i zapisów do bazy; przekaż Architektowi przez BOARD.md. |
