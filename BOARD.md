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
| ROTA-TARGET-EQUITY-WEIGHT-TOO-WEAK | CC | Architekt | — (finding, nie implementacja) | `arch/FINDING_2026-09-20_TARGET_EQUITY_WEIGHT_TOO_WEAK_UNDER_SHORTFALL.md` | OWNER_DECISION_NEEDED | **Krytyczne wg ownera: "bez prawie równego podziału Rota jest do wyrzucenia."** Żywy przykład (Royal, październik 2026, 6 osób, wszyscy cel=176h, zero absencji): solver dał rozstrzał 48h-168h. Hipoteza ownera (cofnąć `EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE` z 15 września) sprawdzona i OBALONA -- usunięty mechanizm awaryjny uruchamiał się tylko przy niekompletnym wektorze celów (cytat z jego własnego docstringa), a Royal ma wektor kompletny, więc cofnięcie nic by nie zmieniło. Prawdziwa przyczyna znaleziona i odtworzona bezpośrednio na żywym obiekcie: `TARGET_EQUITY_WEIGHT=1` w `rota/planning/fairness.py` jest realne, ale za słabe, żeby solver wybierał najrówniejszy podział spośród rozwiązań równie dobrych wg TARGET-01 (które jest dowodliwie STAŁE niezależne od rozkładu, gdy pokrycie zmian jest HARD). Eksperyment: wymuszenie sztywnego capu na rozstrzale `completion_pct` jako HARD constraint -- KAŻDY poziom (50/30/15/8 punktów %) rozwiązał się szybko i `optimization_complete=True`, dając 120-132h zamiast 48-168h. Żadne realne ograniczenie (odpoczynek, zakaz 3 zmian z rzędu, rotacja D/N) nie blokuje równego podziału -- to czysto słabość wagi tie-breaka. Nie regresja z 15 września -- prawdopodobnie słabość istniała od dawna, po prostu nie została wcześniej tak mocno naświetlona. Pełne dane, tabela eksperymentu i kandydackie kierunki naprawy w pliku findingu. CC nie projektuje rozwiązania solvera -- to wymaga architekta+Codex, jak poprzedni finding T058/T059 w tym samym katalogu. |
