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
| ROTA-BACKEND-TASK-SCOPE-FORMAT-DRIFT | CC | Architekt | — (finding, brak briefu) | `backend.py` niezmieniony od `03e5353` (jeden commit w całej historii); brief `tasks/ROTA-T065/brief.md` | OWNER_DECISION_NEEDED | **`backend.py` nie był nieautoryzowanie zmieniony — sprawdzone `git log --oneline -- backend.py`, dokładnie jeden commit w historii, baseline projektu. Przyczyna jest odwrotna: format brief.md architekta odjechał od kontraktu, którego `backend.py` mechanicznie wymaga, i nikt tego nie złapał, bo mechaniczna bramka nie jest już uruchamiana w bieżącym procesie CC↔Codex/BOARD.md (ostatni realny przebieg: `tasks/ROTA-T055/round_01/tests/backend_output_r4.txt`, 4 września).** `backend.py::read_task_scope()` wymaga LITERALNEJ linii `TASK_SCOPE:` (dwukropek, bez nagłówka markdown) z listą plików jako myślniki (`- plik.py`) — dokładnie tak wyglądał `tasks/ROTA-T055/brief.md` (`TASK_SCOPE:` + myślniki), i wtedy `SIZE_FILE`/`SIZE_FUNC`/`RUFF`/`DIFF_SCOPE` realnie działały. `tasks/ROTA-T065/brief.md` sekcję nazywa `## 19. Literalny TASK_SCOPE` (nagłówek markdown, nie literalne `TASK_SCOPE:`) i wypisuje pliki jako listę numerowaną (`1. `, `2. `...), nie myślnikami. Zweryfikowane bezpośrednim uruchomieniem `read_task_scope()` na tym pliku: `ValueError: TASK_SCOPE missing in brief` — parser nie znajduje sekcji wcale, więc `check_sizes`/`check_ruff`/`check_scope_and_files`/`find_importers` dostają pustą listę i milczą, zamiast wyrzucić błąd na przekroczenie limitu linii pliku/funkcji. **Prośba do architekta: pisząc TASK_SCOPE w każdym brief.md, używać dokładnie formatu `backend.py` już umie parsować — literalna linia `TASK_SCOPE:` (nie nagłówek), pliki jako myślniki, nie lista numerowana** — to jedyna mechaniczna bramka pilnująca limitu wielkości plików/funkcji niezależnie od implementatora; jej ciche wyłączenie zwiększa ryzyko rozrostu kodu (spaghetti) bez sygnału. CC nie zmienia formatu briefów samodzielnie — to decyzja architekta/właściciela co do konwencji pisania briefów. |
| ROTA-T065-PRINT-GAP | Codex | Architekt/CC | `task/ROTA-T065-PRINT-GAP` | audit `eda3b0a` (brief B `8bf47a21484277ffecf0ae7a6223b28fe970c971`) | CODEX_REPORTED | **PASS — architektura CHECKPOINT B zamknięta.** Raport: `tasks/ROTA-T065-PRINT-GAP/round_01/tests/tests_r5.txt`. 11 decyzji jest w briefie jako PRODUCT_TRUTH; stary kontrakt roli przy godzinach usunięto; jedna historyczna etykieta stanowiska ma jawnego ownera/dependency w `ROTA-T065-CONFIGURABLE-ROLES`; PRINT-GAP nie tworzy modelu ról. Jeden export lifecycle i scope pozostają zachowane. Implementacja produkcyjna nadal czeka wyłącznie na techniczną dostępność historycznego stanowiska z dependency. Nie powtarzano audytu prototypu ani nie uruchamiano testów produktu/regresji. |
| ROTA-T065-CONFIGURABLE-ROLES | Architekt | Codex | `task/ROTA-T065-CONFIGURABLE-ROLES` | brief `98226a792b24a293bba24bb67365b741b8403234` | READY_FOR_CODEX | Preimplementation review. OWNER correction frozen: configurable role catalog per Site; every ORDINARY demand has a role; organizational title is separate from role of work; no automatic hierarchy/fallback; manager remains manager when covering seller work; coordinator must explicitly authorize substitution or may choose external support. Verify minimal data owner and no second role/solver pipeline. |
| ROTA-T065-ORDINARY-TIME-AVAILABILITY | Architekt | Codex | `task/ROTA-T065-ORDINARY-TIME-AVAILABILITY` | brief `087c228fbea02964cc9e916a1a93637beffc1112` | READY_FOR_CODEX | Preimplementation review after/alongside configurable roles. Dated daily hourly unavailability extends existing append-only AvailabilityRecord and one shared interval-overlap oracle for solver + manual validation. No D/N or shift-row semantics, no second availability engine. |
| ROTA-T065-MANUAL-MIDDLE-SHIFT | Architekt | Codex | `task/ROTA-T065-MANUAL-MIDDLE-SHIFT` | brief `41f2e4c84fc8498dd87eae7b069b9ac0a659b317` | READY_FOR_CODEX | Preimplementation review after configurable roles. Manual seasonal/event middle work only through existing manual-correction child ScheduleVersion; real work with normal HARD/deviation rules, mandatory performed role, no S1 exemptions, no solver/generator or separate history. |
