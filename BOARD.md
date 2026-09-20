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
| ROTA-TARGET-EQUITY-WEIGHT-TOO-WEAK | Architekt | CC | — (diagnostyka, bez implementacji) | `arch/FINDING_2026-09-20_TARGET_EQUITY_WEIGHT_TOO_WEAK_UNDER_SHORTFALL.md` | READY_FOR_CODEX | **OWNER 2026-09-20: najpierw Task sprawdzający, żadnego grzebania w wagach.** Zbadaj, czy nierówność Royal (październik 2026, 6 LOCAL, równe cele 176h, bez absencji) jest regresją, zmianą danych wejściowych czy dawną słabością ujawnioną na tym obiekcie. Odtwórz wcześniejszą wersję, która według OWNERA dzieliła godziny poprawnie, i bieżącą na **identycznym snapshotcie wejść** (Site, roster, targety, shift demands, historia, reguły, absence i wszystkie pozostałe fakty wpływające na PLAN), z tym samym trybem PLAN i porównywalnymi ustawieniami solvera; nie pracuj na mutowanej bazie produkcyjnej i nie zapisuj danych Royal do repo. Jeżeli brak wiarygodnej wcześniejszej wersji/snapshotu, napisz wprost, czego nie da się ustalić — nie ogłaszaj regresji na podstawie pamięci. Porównaj godziny **każdej osoby**, rozstrzał, rytm D/N (liczba/rozłożenie D i N oraz odpoczynek), spełnienie HARD, status optymalizacji, limit/gap i czasy; oddziel różnice algorytmu od różnic wejść, losowości i prezentacji godzin (DST). Wskaż pierwszy commit/zmianę, przy której na tych samych danych następuje pogorszenie, albo udokumentuj brak takiego punktu. Nie zakładaj, że usunięcie fallbacku 15.09 jest przyczyną; finding już wykazał, że dla kompletnego wektora celów nie działał. **OWNER: rytm D/N ma pierwszeństwo przed dokładnością indywidualnego celu godzin; różnice godzin można wyrównywać w następnym miesiącu, lecz skrajnego rozstrzału nie uznawać automatycznie za poprawny.** Deliverable: krótki raport + odtwarzalny read-only reproduktor / opis ograniczeń dowodowych na osobnym branchu diagnostycznym, bez zmian produkcyjnego solvera. Nie zmieniaj wag, HARD capów, priorytetów, limitów/gapu ani innych zasad. Po raporcie przekaż wynik Architektowi; dopiero wtedy projektujemy najmniejszy fix. |
