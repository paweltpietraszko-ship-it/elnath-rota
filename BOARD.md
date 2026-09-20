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
| ROTA-TARGET-EQUITY-DIAGNOSIS | Architekt | CC | `task/ROTA-TARGET-EQUITY-DIAGNOSIS` | diagnosis `da6be6b` | READY_FOR_CODEX | **OWNER: kontynuuj istniejący Task; zgoda wyłącznie na kontrolowany eksperyment z wagami, nie na zmianę produkcyjną.** Raport `tasks/ROTA-TARGET-EQUITY-DIAGNOSIS/report.md` i reproduktor z `da6be6b` wskazują brak regresji dla Royal między `900ef16` a `e77b9d3`; nie cofaj zmiany z 15.09. W izolowanym środowisku testowym sprawdź kilka wariantów wagi equity istniejącej funkcji celu (bez zmiany innych zasad), na tych samych wejściach Royal/październik 2026 oraz co najmniej jednym innym reprezentatywnym obiekcie. Dla bazowego i każdego wariantu przedstaw godziny wszystkich osób i rozstrzał, jakość rytmu D/N (nie tylko HARD PASS), walidację HARD, status optymalizacji/gap, czas wykonania i zgodność z obecnym budżetem; odróżnij wynik pojedynczego uruchomienia od stabilności rozwiązania. Zachowaj dotychczasowe limity czasu, 1% gap i obowiązujące reguły HARD. **OWNER: rytm D/N ważniejszy niż dokładne osiągnięcie indywidualnego celu godzin; różnice godzin można wyrównać w następnym miesiącu, ale rozstrzał Royal 48–168h jest nieakceptowalny.** Nie dodawaj HARD capu, nie zmieniaj produkcyjnych wag/priorytetów ani kodu solvera na branchu do merge; eksperymentalne modyfikacje tylko odizolowane, bez zapisów do produkcyjnej bazy i bez PII w repo. Zapisz krótki raport, reproduktor i rekomendację najmniejszej skutecznej zmiany na branchu tego samego Tasku; po zakończeniu wpisz przekazanie do Architekta w BOARD.md. Żadnego merge bez osobnej decyzji OWNERA. |
