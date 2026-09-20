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
| ROTA-OCHRONA-EQUITY-SURGICAL-FIX | Architekt | CC | `task/ROTA-OCHRONA-EQUITY-SURGICAL-FIX` | static re-audit exact SHA `b68c615488e33627bc18bbac91c09dd9e40c522b` | READY_FOR_CODEX | **STATYCZNY RE-AUDYT: PASS dla naprawy dwóch findingów z `7503759`, NIE końcowy PASS całej implementacji ani zgoda na merge.** W diffie `b68c615` hierarchia dla OCHRONA jest jawnie `LOCAL > sufit > wyrównanie godzin > rytm/weekend/holiday` (prefer-local weight przewyższa górną granicę łącznej kary za wszystkie przekroczenia i niższe składniki); to odpowiada doprecyzowanej decyzji OWNERA, że EXTERNAL_SUPPORT jest ostatecznością. Dodano 4 celowane testy: brak targetu+absencja, mieszany wektor, fixed hours przy REPLAN oraz LOCAL vs EXTERNAL przy przekroczeniu sufitu; skorygowano ostrzeżenie OCHRONA, ORDINARY ma dawny tekst. **Granice weryfikacji:** nie uruchamiałem testów ani grafiku i nie mogę potwierdzić deklarowanych 678 wyników / 15 baseline failures, jakości D/N, czasu działania czy zgodności wyników na żywych obiektach; 4 nowe testy izolują solver na syntetycznym stanie, nie zastępują integracyjnego sprawdzenia PLAN/REPLAN/precheck z DB i nie dowodzą wszystkich przypadków absencji. Uwaga redakcyjna: komunikat OCHRONA „godziny zostaną rozdzielone równo” sugeruje gwarancję bezwarunkową; rzeczywisty podział zależy od HARD i dostępności, lepiej „możliwie równomiernie” przy okazji następnej korekty, bez poszerzania tasku. **Dalsza ścieżka:** CC nie musi ponownie zmieniać solvera na podstawie poprzednich dwóch findingów; przygotować do niezależnego audytu Codex/Antigravity gdy dostępny, z dokładnym SHA i wynikami testów integracyjnych; merge tylko po osobnej decyzji OWNERA. |
