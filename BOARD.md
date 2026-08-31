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
| BOARD-03 | Codex | Architekt/CC | docs/variant-b-joint-evaluation-batch2 | 77763c7 | CODEX_REPORTED | Codex zakończył seedy 60–89: `arch/CODEX_JOINT_EVAL_SEEDS_60-89_2026-08-31.md` @ `77763c7`. Wszystkie 30 sklasyfikowane `BRAK_UWAG` (nie PASS): 30/30 FEASIBLE, kandydaci i wybór; 0 nierozwiązanych decyzji, deviations, błędów i nieoczekiwanych ostrzeżeń; 13 przebiegów poprawnie użyło łącznie 18 EXTERNAL. Nie przeliczano HARD ani bilansów i nie użyto nowych progów. Ważne do konsolidacji: finding CC `month_balance <= -20 h` nie jest nowym defektem — `tasks/ROTA-T044/brief.md:102-106` zawiera wcześniejszą decyzję OWNERA, że strukturalny miesięczny deficyt przy ciasnej obsadzie jest informacją bilansową/sprawą kadrową i „Nie Task”; Wariant B świadomie nie daje kontekstu kwartału. Próg `-20 h` nie pochodzi z kontraktu. Zmiana tej decyzji wymagałaby nowego rozstrzygnięcia OWNERA, nie automatycznej promocji z evaluatora. Pozostaje ocena architekta seedów 90–119 i wspólna konsolidacja. |
