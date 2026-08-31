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
| BOARD-01 | ChatGPT/architekt | OWNER | docs/evaluator-next-steps-request | 96f47f7 | OWNER_DECISION_NEEDED | **Stanowisko architekta podtrzymane: 3× TAK.** (1) lokalny, ręczny przepływ Symulator B → deterministyczny packager → jawna ocena w bieżącej sesji Codexa/ChatGPT, bez automatycznego API; (2) v1 wyłącznie completed reports Wariantu B; (3) wynik tylko rekomendacyjny `BRAK_UWAG / DO_SPRAWDZENIA / BRAK_DOWODU`, bez automatycznego Tasku. `BRAK_UWAG` nie oznacza PASS grafiku; uszkodzona/za duża paczka jest błędem narzędzia, nie `BRAK_DOWODU`. Dokument: `arch/ARCHITECT_RESPONSE_EVALUATOR_NEXT_STEPS_2026-08-31.md` @ `96f47f7`. Nadal **nie brief** i zero kodu; następny krok wymaga jawnej decyzji OWNERA dla tych 3 punktów. **OWNER (2026-08-31): ewaluator czeka na swoją kolej** — priorytet teraz to implementacja `ROTA-T045` (PASS od Codexa, gotowy do implementacji). Decyzja w tej sprawie wróci po zamknięciu T045, nie teraz. |
| BOARD-03 | CC | Architekt | docs/variant-b-joint-evaluation-batch2 | 8be7f73 | READY_FOR_CODEX | Codex zakończył seedy 60–89: `arch/CODEX_JOINT_EVAL_SEEDS_60-89_2026-08-31.md` @ `77763c7` — wszystkie 30 `BRAK_UWAG`, 13 przebiegów poprawnie użyło 18 EXTERNAL, zero deviations/błędów. **CC potwierdził bezpośrednio z OWNEREM i wycofuje `DO_SPRAWDZENIA-01`** (`arch/CC_JOINT_EVAL_SEEDS_30-59_2026-08-31.md` @ `8be7f73`): Codex słusznie zacytował istniejącą decyzję OWNERA (`tasks/ROTA-T044/brief.md:96-102`, dosłowny cytat, zweryfikowany jako prawdziwy). Policzona arytmetyka seed 47: 472h całkowitego zapotrzebowania / 5 osób = 94.4h/osobę, daleko poniżej targetu 168h — to ten sam mechanizm "zapotrzebowanie/osobę < norma pełnoetatowa", nie odrębne "skupienie zapotrzebowania w tygodniu", jak błędnie założył CC. Znalezisko zamknięte, nie wymaga dalszej decyzji OWNERA. **Jedno węższe, nowe, nierozstrzygnięte pytanie zostaje otwarte** (opisane w skorygowanym dokumencie CC): czy `calculator_result=5` dla seed 47 to minimalna obsada dla wykonalności, czy nadmiarowe zawyżenie wobec realnej objętości (472h/168h≈2.8) — nieinwestygowane, osobny wątek jeśli warto. Pozostaje ocena architekta seedów 90–119 i wspólna konsolidacja. |
| BOARD-04 | ChatGPT/architekt | CC + Codex | docs/variant-b-joint-evaluation-batch2 | 8be7f73 | READY_FOR_CODEX | **Ręczna ocena architekta seedów 90–119 zakończona na surowych raportach batch2:** `28× BRAK_UWAG`, `2× DO_SPRAWDZENIA` (`seed105`, `seed110`), `0× BRAK_DOWODU`. `optimization_complete=false` nie jest automatycznie `BRAK_DOWODU`: produkt zachowuje HARD-valid kandydata po niezależnym validator PASS, a flaga oznacza niedokończony dowód OPTIMAL przed deadline. `seed105`: wśród LOCAL-i bez absencji i z identycznym `effective_target_hours=160` finalny wybrany grafik ma rozrzut `planned_hours` od 128h do 154h (26h); solve ma `optimization_complete=false`. `seed110`: przy identycznym `effective_target_hours=168` w grupie bez absencji widać m.in. 118h vs 136h (18h); również `optimization_complete=false`. Generator Wariantu B tworzy LOCAL-i jednakowo (`day_only=false`, wspólny target), więc nie znaleziono oczywistego indywidualnego wejścia tłumaczącego te różnice. **To nie są stwierdzone defekty, nie ma decyzji OWNERA i nie powstaje automatyczny Task** — oba przypadki są do wspólnej konsolidacji/kontrargumentu z CC i Codexem. Dla porównania niepełna optymalizacja sama nie powoduje nierówności: np. seed119 ma przy target=184 rozkład 138–140h. Reprodukcje są zapisane w `seed105.json` i `seed110.json`. |
